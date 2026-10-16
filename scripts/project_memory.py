#!/usr/bin/env python3
"""Manage project records, validate configuration, and fingerprint deliverables.

Python 3.9+; standard library only. Structure and identity checks do not replace
actual review of research accuracy, teaching quality, and visual layout.
"""
import argparse
from copy import deepcopy
from datetime import date, datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import uuid

SCHEMA = 'research-briefing/2'
LEGACY = 'research-briefing/1'
VERSION = '1.2.1'
SEMVER = (r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)'
          r'(?:-((?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)'
          r'(?:\.(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*))*))?'
          r'(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?')
META = '.research-briefing'
MEMORY = '研究辅助文档'
KINDS = ('report', 'report-pdf', 'slides', 'slides-pdf', 'speaker-script', 'author-explainer')
STAGES = ('initialized', 'planning', 'researching', 'drafting', 'sample-review',
          'authoring', 'reviewing', 'awaiting-review', 'delivered')
KEYS = ('standards', 'guide', 'quality', 'content', 'evidence', 'progress')
EXTENSIONS = {'report': ('.docx', '.md', '.tex', '.html'), 'report-pdf': ('.pdf',),
              'slides': ('.pptx',), 'slides-pdf': ('.pdf',),
              'speaker-script': ('.docx', '.md', '.pdf'), 'author-explainer': ('.docx', '.md', '.pdf')}


class MemoryError(ValueError):
    pass


def emit(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def encoded(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'


def now():
    return datetime.now(timezone.utc).isoformat()


def require(condition, message):
    if not condition:
        raise MemoryError(message)


def write_new(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    stream = path.open('x', encoding='utf-8', newline='\n')
    try:
        with stream:
            stream.write(payload)
    except BaseException:
        path.unlink()
        raise


def inside(root, value, relative=False):
    require(isinstance(value, str) and bool(value.strip()), 'Path must be a non-empty string.')
    raw = Path(value)
    require(not relative or not raw.is_absolute(), 'Configuration paths must be project-relative: ' + value)
    target = (raw if raw.is_absolute() else root / raw).resolve()
    try:
        rel = target.relative_to(root)
    except ValueError as exc:
        raise MemoryError('Path must remain inside the selected project: ' + value) from exc
    require(bool(rel.parts), 'Select a file, not the project root.')
    return target, rel.as_posix()


def fingerprint(path):
    require(path.is_file(), 'File is missing or is not a regular file: ' + str(path))
    before = path.stat()
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    after = path.stat()
    require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns),
            'File changed while being read: ' + str(path))
    return {'bytes': after.st_size, 'sha256': digest.hexdigest()}


def reject_json_constant(value):
    raise ValueError('Non-finite JSON constant is not supported: ' + value)


def finite_json_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError('JSON number exceeds the finite float range: ' + value)
    return number


def load_json(path, with_identity=False):
    try:
        before = path.stat() if with_identity else None
        payload = path.read_bytes()
        after = path.stat() if with_identity else None
        data = json.loads(payload.decode('utf-8-sig'), parse_constant=reject_json_constant,
                          parse_float=finite_json_float)
    except (OSError, ValueError) as exc:
        raise MemoryError('Cannot read JSON: ' + str(path)) from exc
    if with_identity:
        require((before.st_size, before.st_mtime_ns, before.st_dev, before.st_ino)
                == (after.st_size, after.st_mtime_ns, after.st_dev, after.st_ino),
                'Configuration changed while being read; retry after reading it.')
        return data, {'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}
    return data


def object_fields(value, required, label, optional=()):
    require(isinstance(value, dict), label + ' must be an object.')
    require(set(required) <= set(value), label + ' is missing fields: ' + ', '.join(set(required) - set(value)))
    require(set(value) <= set(required) | set(optional), label + ' contains unknown fields.')


def nullable_text(value, label):
    require(value is None or isinstance(value, str) and bool(value.strip()), label + ' must be non-empty text or null.')


def positive_finite_number(value):
    return (type(value) is int and value > 0
            or type(value) is float and math.isfinite(value) and value > 0)


def string_list(value, label, choices=None, nonempty=False):
    require(isinstance(value, list) and (bool(value) or not nonempty), label + ' must be a list.')
    require(all(isinstance(v, str) and bool(v.strip()) for v in value), label + ' requires non-empty strings.')
    require(len(value) == len(set(value)), label + ' contains duplicates.')
    require(choices is None or set(value) <= set(choices), label + ' contains unsupported values.')


def config_path(root, value, label, must_exist=False):
    path, rel = inside(root, value, relative=True)
    require(value == rel, label + ' requires a normalized project-relative path with / separators: ' + rel)
    require(not path.exists() or path.is_file(), label + ' must refer to a file: ' + rel)
    require(not must_exist or path.is_file(), label + ' file is missing: ' + rel)
    return path, rel


def expected_items(root, items, kinds):
    require(isinstance(items, list), 'delivery.expected_artifacts must be a list.')
    seen = set()
    for item in items:
        object_fields(item, ('kind', 'path', 'version', 'required'), 'Expected artifact')
        require(item['kind'] in kinds, 'Expected artifact kind must belong to deliverables.')
        path, rel = config_path(root, item['path'], 'Expected artifact')
        require(rel.casefold() not in seen, 'Duplicate expected artifact path: ' + rel)
        seen.add(rel.casefold())
        require(path.suffix.lower() in EXTENSIONS[item['kind']], 'Unexpected file extension for ' + item['kind'] + ': ' + rel)
        require(isinstance(item['version'], str) and bool(item['version'].strip()), 'Expected artifact version must be non-empty text.')
        require(type(item['required']) is bool, 'Expected artifact required must be boolean.')
    return items


def validate_config(root, data):
    require(isinstance(data, dict), 'Project configuration must be an object.')
    require(data.get('schema_version') in (SCHEMA, LEGACY), 'Unsupported project schema.')
    if data['schema_version'] == LEGACY:
        require(isinstance(data.get('brief'), dict), 'Legacy brief must be an object.')
        string_list(data.get('deliverables'), 'deliverables', KINDS, True)
        require(data.get('memory_profile') in ('compact', 'full'), 'Invalid memory_profile.')
        require(isinstance(data.get('memory_documents'), dict), 'Invalid legacy memory_documents.')
        for value in data['memory_documents'].values():
            config_path(root, value, 'Memory document', True)
        return {'migration_required': True, 'planned_references': []}
    object_fields(data, ('schema_version', 'skill_version', 'topic', 'deliverables', 'memory_profile',
                        'brief', 'research', 'presentation', 'delivery', 'memory_documents', 'memory_history'),
                  'Project', optional=('extensions',))
    require(isinstance(data['skill_version'], str) and re.fullmatch(SEMVER, data['skill_version']),
            'skill_version must be a valid SemVer origin value; schema_version controls compatibility.')
    require(isinstance(data.get('extensions', {}), dict), 'extensions must be an object; domain semantics are reviewed separately.')
    require(isinstance(data['topic'], str) and bool(data['topic'].strip()), 'topic must be non-empty text.')
    string_list(data['deliverables'], 'deliverables', KINDS, True)
    require(data['memory_profile'] in ('compact', 'full'), 'Invalid memory_profile.')
    brief = data['brief']
    object_fields(brief, ('purpose', 'audiences', 'author_baseline', 'focus', 'language', 'length_budget', 'duration_minutes'), 'brief')
    for key in ('purpose', 'author_baseline', 'length_budget'):
        nullable_text(brief[key], 'brief.' + key)
    object_fields(brief['audiences'], ('report', 'slides', 'author_explainer'), 'brief.audiences')
    for key, value in brief['audiences'].items():
        nullable_text(value, 'brief.audiences.' + key)
    string_list(brief['focus'], 'brief.focus')
    require(isinstance(brief['language'], str) and bool(brief['language'].strip()), 'brief.language must be non-empty text.')
    duration = brief['duration_minutes']
    if isinstance(duration, dict):
        object_fields(duration, ('min', 'max'), 'brief.duration_minutes')
        require(all(positive_finite_number(n) for n in duration.values()) and duration['min'] <= duration['max'],
                'Duration range requires finite positive min <= max.')
    else:
        require(duration is None or positive_finite_number(duration), 'Duration must be finite and positive or null.')
    research = data['research']
    object_fields(research, ('cutoff_date', 'scope', 'inference_policy'), 'research')
    if research['cutoff_date'] is not None:
        require(isinstance(research['cutoff_date'], str)
                and re.fullmatch(r'\d{4}-\d{2}-\d{2}', research['cutoff_date']),
                'cutoff_date must use YYYY-MM-DD or null.')
        try:
            date.fromisoformat(research['cutoff_date'])
        except ValueError as exc:
            raise MemoryError('cutoff_date must be a valid ISO date.') from exc
    string_list(research['scope'], 'research.scope')
    nullable_text(research['inference_policy'], 'research.inference_policy')
    presentation = data['presentation']
    object_fields(presentation, ('visual_configuration', 'timing_plan', 'image_policy', 'preference_profile'), 'presentation')
    planned = []
    for key in ('visual_configuration', 'timing_plan'):
        if presentation[key] is not None:
            path, rel = config_path(root, presentation[key], 'presentation.' + key)
            if not path.exists():
                planned.append(rel)
    for key in ('image_policy', 'preference_profile'):
        nullable_text(presentation[key], 'presentation.' + key)
    delivery = data['delivery']
    object_fields(delivery, ('formats', 'preserve_inputs', 'current_stage', 'expected_artifacts'), 'delivery')
    require(isinstance(delivery['formats'], dict) and set(delivery['formats']) <= set(KINDS), 'Invalid delivery.formats keys.')
    for value in delivery['formats'].values():
        require(isinstance(value, str) and bool(value.strip()), 'Format values must be non-empty text.')
    require(type(delivery['preserve_inputs']) is bool, 'preserve_inputs must be boolean.')
    require(delivery['current_stage'] in STAGES, 'Invalid current_stage.')
    expected_items(root, delivery['expected_artifacts'], data['deliverables'])
    object_fields(data['memory_documents'], KEYS, 'memory_documents')
    for value in data['memory_documents'].values():
        config_path(root, value, 'Active memory document', True)
    require(isinstance(data['memory_history'], list), 'memory_history must be a list.')
    for record in data['memory_history']:
        object_fields(record, ('profile', 'documents', 'retired_at_utc'), 'Memory history')
        require(record['profile'] in ('compact', 'full'), 'Invalid historical profile.')
        object_fields(record['documents'], KEYS, 'Historical memory documents')
        nullable_text(record['retired_at_utc'], 'retired_at_utc')
        for value in record['documents'].values():
            config_path(root, value, 'Historical memory source', True)
    return {'migration_required': False, 'planned_references': planned}


def render_documents(root, config, history=None):
    resources = load_json(Path(__file__).resolve().parent.parent / 'assets/memory-templates.json')
    documents, mapping = {}, {}
    values = {'topic': config['topic'], 'deliverables': '、'.join(config['deliverables'])}
    for item in resources['profiles'][config['memory_profile']]:
        bodies = []
        for key in item['keys']:
            text = resources['templates'][key]
            for name, value in values.items():
                text = text.replace('{{' + name + '}}', value)
            if len(item['keys']) > 1:
                text = re.sub(r'^(#{1,5}) ', r'\1# ', text, flags=re.MULTILINE)
            bodies.append(text.rstrip())
            mapping[key] = MEMORY + '/' + item['filename']
        body = '\n\n'.join(bodies) + '\n'
        if len(bodies) > 1:
            body = '# ' + config['topic'] + '｜' + item['title'] + '\n\n' + body
        if history:
            sources = list(dict.fromkeys(history[key] for key in item['keys']))
            links = '、'.join('[' + Path(p).name + '](' + os.path.relpath(root / p, root / MEMORY).replace('\\', '/') + ')' for p in sources)
            body = ('> 活动记录（由 compact 升级）。已有内容的历史来源：' + links + '。\n'
                    '> 原记录保留供读取；后续决定与新内容仅在本活动记录维护。完成正文整理后可移除此入口。\n\n' + body)
        path, _ = inside(root, MEMORY + '/' + item['filename'])
        documents[path] = body
    return documents, mapping


def create_batch(documents):
    collisions = [str(p) for p in documents if p.exists()]
    require(not collisions, 'Existing files are preserved; operation stopped: ' + ', '.join(collisions))
    created = []
    try:
        for path, text in documents.items():
            write_new(path, text)
            created.append(path)
    except BaseException:
        for path in reversed(created):
            path.unlink()
        raise
    return created


def initialize(args):
    root = Path(args.root).resolve()
    require(bool(args.topic.strip()), 'Topic must be non-empty.')
    require(bool(args.language.strip()), 'Language metadata must be non-empty.')
    config = {'schema_version': SCHEMA, 'skill_version': VERSION, 'topic': args.topic.strip(),
              'deliverables': list(dict.fromkeys(args.deliverable)), 'memory_profile': args.memory_profile,
              'brief': {'purpose': None, 'audiences': {'report': None, 'slides': None, 'author_explainer': None},
                        'author_baseline': None, 'focus': [], 'language': args.language, 'length_budget': None, 'duration_minutes': None},
              'research': {'cutoff_date': None, 'scope': [], 'inference_policy': None},
              'presentation': {'visual_configuration': None, 'timing_plan': None, 'image_policy': None, 'preference_profile': None},
              'delivery': {'formats': {}, 'preserve_inputs': True, 'current_stage': 'initialized', 'expected_artifacts': []},
              'memory_documents': {}, 'memory_history': [], 'extensions': {}}
    documents, config['memory_documents'] = render_documents(root, config)
    cfg, _ = inside(root, META + '/project.json')
    documents[cfg] = encoded(config)
    create_batch(documents)
    emit({'status': 'initialized', 'root': str(root), 'deliverables': config['deliverables'],
          'created': [p.relative_to(root).as_posix() for p in documents]})
    return 0


def update(args):
    root = Path(args.root).resolve()
    cfg, _ = inside(root, META + '/project.json')
    original_identity = fingerprint(cfg)
    original = load_json(cfg)
    validate_config(root, original)
    data, documents = deepcopy(original), {}
    if data['schema_version'] == LEGACY:
        require(args.migrate, 'Legacy configuration is preserved; use update --migrate explicitly.')
        data['schema_version'], data['skill_version'] = SCHEMA, VERSION
        audience = data['brief'].pop('audience', None)
        data['brief']['audiences'] = {'report': audience, 'slides': audience,
                                     'author_explainer': data['brief'].get('author_baseline')}
        data['presentation'].update({'timing_plan': None, 'preference_profile': None})
        data['delivery']['expected_artifacts'] = []
        data['memory_history'] = []
        backup, _ = inside(root, META + '/migrations/project-v1-' + uuid.uuid4().hex[:12] + '.json')
        documents[backup] = cfg.read_text(encoding='utf-8-sig')
    data['deliverables'] = list(dict.fromkeys(data['deliverables'] + (args.add_deliverable or [])))
    if args.memory_profile and args.memory_profile != data['memory_profile']:
        require(data['memory_profile'] == 'compact' and args.memory_profile == 'full', 'Only compact -> full promotion is supported.')
        history = deepcopy(data['memory_documents'])
        data['memory_history'].append({'profile': 'compact', 'documents': history, 'retired_at_utc': now()})
        data['memory_profile'] = 'full'
        additions, data['memory_documents'] = render_documents(root, data, history)
        documents.update(additions)
    if args.expected_artifacts:
        path, _ = inside(root, args.expected_artifacts)
        data['delivery']['expected_artifacts'] = load_json(path)
    if args.stage:
        data['delivery']['current_stage'] = args.stage
    created = create_batch(documents)
    temporary = cfg.with_name('.project-pending-' + uuid.uuid4().hex + '.json')
    try:
        validate_config(root, data)
        write_new(temporary, encoded(data))
        require(fingerprint(cfg) == original_identity, 'Configuration changed during update; retry after reading it.')
        os.replace(temporary, cfg)
    except BaseException:
        if temporary.exists():
            temporary.unlink()
        for path in reversed(created):
            path.unlink()
        raise
    emit({'status': 'updated', 'schema_version': SCHEMA, 'tool_version': VERSION, 'deliverables': data['deliverables'],
          'memory_profile': data['memory_profile'], 'created': [p.relative_to(root).as_posix() for p in created]})
    return 0


def check_delivery(root, expected, kinds=()):
    findings = [{'path': item['path'], 'kind': item['kind'], 'status': 'missing-required'}
                for item in expected if item['required'] and not (root / item['path']).is_file()]
    configured = {item['kind'] for item in expected}
    findings.extend({'kind': kind, 'status': 'unconfigured-deliverable'} for kind in kinds if kind not in configured)
    return findings


def validate_command(args):
    root = Path(args.root).resolve()
    cfg, _ = inside(root, args.config)
    data = load_json(cfg)
    result = validate_config(root, data)
    findings = check_delivery(root, data['delivery'].get('expected_artifacts', []), data['deliverables']) if args.check_delivery else []
    emit({'status': 'valid' if not findings else 'incomplete', 'schema_version': data['schema_version'],
          **result, 'findings': findings})
    return 1 if findings else 0


def snapshot(args):
    root = Path(args.root).resolve()
    require(root.is_dir(), 'Project root must already exist.')
    require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}', args.label), 'Invalid snapshot label (letters/digits/dot/underscore/hyphen; max 80).')
    output, rel_output = inside(root, META + '/snapshots/' + args.label + '.json')
    require(not output.exists(), 'Snapshot already exists; choose a new label: ' + rel_output)
    expected, identity = [], None
    files = args.file or []
    if args.expected:
        cfg, rel = inside(root, META + '/project.json')
        config, config_identity = load_json(cfg, with_identity=True)
        validate_config(root, config)
        require(config['schema_version'] == SCHEMA, 'Use update --migrate before expected-delivery checks.')
        expected = config['delivery']['expected_artifacts']
        require(bool(expected), 'Configure delivery.expected_artifacts before using --expected.')
        missing = check_delivery(root, expected, config['deliverables'])
        require(not missing, 'Delivery configuration is incomplete: ' + encoded(missing))
        identity = {'path': rel, **config_identity}
        if not files:
            files = [item['path'] for item in expected if (root / item['path']).is_file()]
    require(bool(files), 'Supply --file or --expected with existing deliverables.')
    entries, seen = [], set()
    for value in files:
        path, rel = inside(root, value)
        if rel.casefold() not in seen:
            entries.append({'path': rel, **fingerprint(path)})
            seen.add(rel.casefold())
    omitted = [item['path'] for item in expected if item['required'] and item['path'].casefold() not in seen]
    require(not omitted, 'Required deliverables were omitted from --file: ' + ', '.join(omitted))
    payload = {'schema_version': SCHEMA, 'label': args.label, 'created_at_utc': now(), 'files': entries}
    if args.expected:
        payload.update({'expected_artifacts': expected, 'config_identity': identity})
        require(fingerprint(cfg) == config_identity, 'Configuration changed during snapshot; retry after reading it.')
    write_new(output, encoded(payload))
    emit({'status': 'recorded', 'manifest': rel_output, 'files': len(entries), 'expected_bound': args.expected})
    return 0


def verify(args):
    root = Path(args.root).resolve()
    manifest, _ = inside(root, args.manifest)
    data = load_json(manifest)
    require(isinstance(data, dict) and data.get('schema_version') in (SCHEMA, LEGACY), 'Unsupported snapshot schema.')
    entries = data.get('files')
    require(isinstance(entries, list) and bool(entries), 'Snapshot must contain file entries.')
    findings, seen = [], set()
    for entry in entries:
        require(isinstance(entry, dict) and isinstance(entry.get('path'), str), 'Malformed snapshot entry.')
        path, rel = inside(root, entry['path'], relative=True)
        sha, size = entry.get('sha256'), entry.get('bytes')
        require(rel.casefold() not in seen and isinstance(sha, str) and re.fullmatch(r'[0-9a-f]{64}', sha)
                and type(size) is int and size >= 0, 'Invalid or duplicate snapshot entry: ' + rel)
        seen.add(rel.casefold())
        if not path.is_file():
            findings.append({'path': rel, 'status': 'missing'})
        else:
            current = fingerprint(path)
            if current != {'bytes': size, 'sha256': sha}:
                findings.append({'path': rel, 'status': 'changed', 'expected': {'bytes': size, 'sha256': sha}, 'actual': current})
    if 'expected_artifacts' in data:
        expected_items(root, data['expected_artifacts'], KINDS)
        findings.extend({'path': item['path'], 'status': 'missing-from-manifest'} for item in data['expected_artifacts']
                        if item['required'] and item['path'].casefold() not in seen)
    config_status = 'not-bound'
    if 'config_identity' in data:
        entry = data['config_identity']
        object_fields(entry, ('path', 'bytes', 'sha256'), 'Config identity')
        path, _ = inside(root, entry['path'], relative=True)
        require(type(entry['bytes']) is int and entry['bytes'] >= 0 and isinstance(entry['sha256'], str)
                and re.fullmatch(r'[0-9a-f]{64}', entry['sha256']), 'Invalid config identity.')
        config_status = 'missing' if not path.is_file() else 'match' if fingerprint(path) == {'bytes': entry['bytes'], 'sha256': entry['sha256']} else 'changed'
    emit({'status': 'match' if not findings else 'different', 'checked': len(entries),
          'config_status': config_status, 'findings': findings})
    return 0 if not findings else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init', help='Create records without overwriting files.')
    init.add_argument('--topic', required=True)
    init.add_argument('--deliverable', choices=KINDS, action='append', required=True)
    init.add_argument('--memory-profile', choices=('compact', 'full'), default='compact')
    init.add_argument('--language', default='zh-CN')
    init.set_defaults(run=initialize)
    change = sub.add_parser('update', help='Add deliverables, explicitly migrate v1, or promote compact records.')
    change.add_argument('--migrate', action='store_true')
    change.add_argument('--add-deliverable', choices=KINDS, action='append')
    change.add_argument('--memory-profile', choices=('compact', 'full'))
    change.add_argument('--expected-artifacts', help='Project-relative JSON list; replaces the expected artifact list.')
    change.add_argument('--stage', choices=STAGES)
    change.set_defaults(run=update)
    validate = sub.add_parser('validate-config', help='Check configuration structure; planned outputs may be missing.')
    validate.add_argument('--config', default=META + '/project.json')
    validate.add_argument('--check-delivery', action='store_true')
    validate.set_defaults(run=validate_command)
    snap = sub.add_parser('snapshot', help='Record file fingerprints; --expected binds configured delivery scope.')
    snap.add_argument('--label', required=True)
    snap.add_argument('--file', action='append')
    snap.add_argument('--expected', action='store_true')
    snap.set_defaults(run=snapshot)
    check = sub.add_parser('verify', help='Return 0 for a match, 1 for differences, 2 for invalid input.')
    check.add_argument('--manifest', required=True)
    check.set_defaults(run=verify)
    for command in (init, change, validate, snap, check):
        command.add_argument('--root', required=True)
    args = parser.parse_args(argv)
    try:
        return args.run(args)
    except (MemoryError, OSError, KeyError, TypeError, AttributeError) as exc:
        emit({'status': 'error', 'message': str(exc)})
        return 2


if __name__ == '__main__':
    sys.exit(main())
