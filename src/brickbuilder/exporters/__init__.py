"""Ordering bundles with per-instance reconciliation and complete native CAD."""
from collections import Counter
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

from .rules import Evidence, Rules
from ..inventory import NativeKey, inventory
from ..ldraw import Document, dumps


@dataclass(frozen=True)
class OrderingItem:
    instance_id: str
    native: NativeKey
    target_part: str | None
    target_colour: int | None
    disposition: str
    evidence: Evidence
    colour_evidence: Evidence | None = None
    catalog_url: str | None = None


def plan_order(document: Document, rules: Rules, *, allow_untested: bool = False) -> tuple[OrderingItem, ...]:
    result = []
    for part in document.model.parts:
        native = NativeKey.of(part)
        rule = rules.part_rule(native)
        if rule.evidence.status == 'rejected':
            raise ValueError(f"Rejected mapping for {native}")
        if rule.manual:
            result.append(OrderingItem(part.instance_id, native, None, None, 'manual',
                                       rule.evidence, catalog_url=rule.catalog_url))
            continue
        assert rule.target is not None  # validated PartRule invariant
        rules.check_target(rule.target, native.colour)
        colour_evidence = None
        target_colour = native.colour
        if rules.market == 'bricklink':
            colour = rules.colour_rule(native.colour)
            target_colour, colour_evidence = colour.target, colour.evidence
            if colour.evidence.status == 'rejected':
                raise ValueError(f"Rejected colour mapping for {native}")
        if not allow_untested and (rule.evidence.status == 'untested' or
                                  (colour_evidence and colour_evidence.status == 'untested')):
            raise ValueError("Untested mapping requires explicit allow_untested / --allow-untested")
        result.append(OrderingItem(part.instance_id, native, rule.target, target_colour,
                                   'import', rule.evidence, colour_evidence))
    if len(result) != len(document.model.parts):
        raise ValueError("Ordering plan quantity mismatch")
    return tuple(result)


def _xml(items: tuple[OrderingItem, ...]) -> str:
    counts = Counter((r.target_part, r.target_colour) for r in items if r.disposition == 'import')
    root = ET.Element('INVENTORY')
    for (part, colour), quantity in sorted(counts.items()):
        item = ET.SubElement(root, 'ITEM')
        for tag, value in [('ITEMTYPE', 'P'), ('ITEMID', str(part)), ('COLOR', str(colour)), ('MINQTY', str(quantity))]:
            ET.SubElement(item, tag).text = value
    ET.indent(root)
    return ET.tostring(root, encoding='unicode') + '\n'


def _ldr(document: Document, items: tuple[OrderingItem, ...]) -> str:
    by_id = {r.instance_id: r for r in items}
    lines = ['0 ORDERING ONLY - NOT A BUILDABLE NATIVE MODEL.',
             '0 Check report.json and add every item listed in manual_additions.json.',
             '0 Importer acceptance and stock are not tested; colours are LDraw IDs.']
    for part in document.model.parts:
        item = by_id[part.instance_id]
        if item.disposition == 'manual':
            continue
        numbers = (*part.transform.position, *(x for row in part.transform.rotation for x in row))
        lines.append(f'1 {part.colour} ' + ' '.join(format(x, '.17g') for x in numbers) + f' {item.target_part}.dat')
    return '\r\n'.join(lines) + '\r\n'


def bundle(document: Document, rules: Rules, *, source_sha256: str,
           allow_untested: bool = False) -> dict[str, str]:
    """Generate in memory; never mutate source parts or combine selections."""
    items = plan_order(document, rules, allow_untested=allow_untested)
    native_counts = Counter(NativeKey.of(p) for p in document.model.parts)
    planned_counts = Counter(item.native for item in items)
    if native_counts != planned_counts or {p.instance_id for p in document.model.parts} != {r.instance_id for r in items}:
        raise ValueError("Per-identity ordering reconciliation failed")
    imported = tuple(r for r in items if r.disposition == 'import')
    manual = tuple(r for r in items if r.disposition == 'manual')
    ordering_name = 'brickowl_partial.ldr' if rules.market == 'brickowl' else 'bricklink_wanted.xml'
    files = {'native.ldr': dumps(document),
             'inventory.json': json.dumps([asdict(q) for q in inventory(document.model)], indent=2) + '\n',
             'manual_additions.json': json.dumps(dict(colour_namespace='ldraw',
                 quantity=len(manual), items=[asdict(r) for r in manual]), indent=2) + '\n'}
    if imported:
        files[ordering_name] = _ldr(document, items) if rules.market == 'brickowl' else _xml(items)
    rules_fingerprint = sha256(json.dumps(asdict(rules), sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    report = dict(rules_fingerprint=rules_fingerprint, ordering_file=ordering_name if imported else None, schema_version=1, source_sha256=source_sha256, model_sha256=document.model.fingerprint(),
                  market=rules.market, part_namespace=f'{rules.market}_catalog_candidate',
                  ordering_colour_namespace='ldraw' if rules.market == 'brickowl' else 'bricklink',
                  complete_quantity=len(items), imported_quantity=len(imported), manual_quantity=len(manual),
                  quantity_reconciliation='pass', per_native_identity_reconciliation='pass',
                  authenticated_import='not_tested', stock='not_tested', physical_build='not_tested',
                  untested_import_instances=sum(r.evidence.status == 'untested' or
                                               bool(r.colour_evidence and r.colour_evidence.status == 'untested') for r in imported),
                  mappings=[asdict(r) for r in items],
                  file_sha256={name: sha256(content.encode()).hexdigest() for name, content in files.items()})
    files['report.json'] = json.dumps(report, indent=2) + '\n'
    return files


def write_bundle(destination: Path, files: dict[str, str]) -> None:
    """Publish an entirely prepared bundle to a new directory, no stale outputs."""
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Export destination already exists: {destination}")
    if not destination.parent.is_dir():
        raise ValueError("Create the destination parent directory first")
    with tempfile.TemporaryDirectory(dir=destination.parent, prefix='brickbuilder-export-') as temp:
        staged = Path(temp)/'bundle'
        staged.mkdir()
        for name, content in files.items():
            if Path(name).name != name or name in ('.', '..'):
                raise ValueError("Bundle filenames must be plain filenames")
            (staged/name).write_text(content, encoding='utf-8', newline='')
        # mkdir is exclusive; unlike directory rename this cannot replace an empty directory.
        destination.mkdir()
        created: list[Path] = []
        try:
            for file in staged.iterdir():
                target = destination/file.name
                with target.open('xb') as stream:
                    created.append(target)
                    stream.write(file.read_bytes())
        except OSError:
            for file in created:
                file.unlink(missing_ok=True)
            try:
                destination.rmdir()
            except OSError:
                pass  # Never remove files created by another process.
            raise


def native_bundle(document: Document, *, source_sha256: str) -> dict[str, str]:
    files = {'native.ldr': dumps(document),
             'inventory.json': json.dumps([asdict(q) for q in inventory(document.model)], indent=2) + '\n'}
    files['report.json'] = json.dumps(dict(source_sha256=source_sha256,
        model_sha256=document.model.fingerprint(), complete_quantity=len(document.model.parts),
        part_namespace='ldraw', colour_namespace='ldraw', format='native',
        authenticated_import='not_tested', physical_build='not_tested',
        file_sha256={name: sha256(content.encode()).hexdigest() for name, content in files.items()}), indent=2) + '\n'
    return files
