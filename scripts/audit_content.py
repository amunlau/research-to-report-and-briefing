#!/usr/bin/env python3
"""Read-only structural and reference audit; never evaluates factual claims."""
import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

LIMITS = [
    "仅实现随包Schema使用的结构子集，不是完整JSON Schema验证器。",
    "不核实原文是否支持结论，不执行计算表达式，不检查事实真实性。",
    "可见限定语仅作字符串覆盖检查，不证明语义充分或实际成品可见。",
    "备注仅检查启用时是否非空，不判断口语稿完整性、自然程度或讲述时长。",
    "本地文件存在性及已记录素材sha256仅在--check-files启用时检查；不为缺失指纹补值。",
    "几何检查仅比较计划中的pt矩形，不检测真实文字、像素溢出或图内标签。",
    "引擎映射仅查结构、引用及声明的覆盖/页序；不读取成品对象，不证明视觉或原生编辑性通过。",
]


class InputError(Exception):
    pass


def reject_constant(value):
    raise InputError("JSON不允许非有限数值: " + value)


def finite_float(value):
    result = float(value)
    if not math.isfinite(result):
        raise InputError("JSON数值超出有限范围: " + value)
    return result


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError("JSON出现重复键: " + key)
        result[key] = value
    return result


def read_json(path):
    try:
        raw = path.read_bytes()
        data = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_object,
                          parse_constant=reject_constant, parse_float=finite_float)
        return data, hashlib.sha256(raw).hexdigest()
    except (InputError, OSError, UnicodeError, ValueError, RecursionError) as exc:
        raise InputError(f"无法读取JSON {path}: {exc}") from None


def contained(root, value):
    try:
        if re.search(r"[\x00-\x1f\x7f]", str(value)):
            raise InputError("路径不得包含控制字符")
        path = Path(value)
        path = (path if path.is_absolute() else root / path).resolve()
        path.relative_to(root)
        return path
    except (OSError, ValueError, TypeError, RuntimeError):
        raise InputError(f"路径必须位于项目root内: {value}") from None


def type_matches(value, expected):
    checks = {"object": lambda: isinstance(value, dict),
              "array": lambda: isinstance(value, list),
              "string": lambda: isinstance(value, str),
              "number": lambda: type(value) in (int, float),
              "integer": lambda: type(value) is int or
                                 (type(value) is float and math.isfinite(value) and value.is_integer()),
              "boolean": lambda: type(value) is bool,
              "null": lambda: value is None}
    return checks.get(expected, lambda: False)()


def schema_errors(value, schema, document, location):
    """Validate only the keywords present in the bundled contract schemas."""
    if "$ref" in schema:
        target = document
        for part in schema["$ref"].removeprefix("#/").split("/"):
            target = target[part.replace("~1", "/").replace("~0", "~")]
        return schema_errors(value, target, document, location)
    if "oneOf" in schema:
        valid = sum(not schema_errors(value, part, document, location)
                    for part in schema["oneOf"])
        return [] if valid == 1 else [(location, "值不匹配oneOf要求")]
    expected = schema.get("type")
    types = expected if isinstance(expected, list) else [expected]
    if expected and not any(type_matches(value, name) for name in types):
        return [(location, "类型错误，要求 " + "/".join(types))]
    errors = []
    if "const" in schema and value != schema["const"]:
        errors.append((location, f"值必须为 {schema['const']}"))
    if "enum" in schema and value not in schema["enum"]:
        errors.append((location, "值不在允许枚举中"))
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.append((location + "." + key, "缺少必需字段"))
        for key, item in value.items():
            child = props.get(key, schema.get("additionalProperties", True))
            if child is False:
                errors.append((location + "." + key, "不允许的字段"))
            elif isinstance(child, dict):
                errors.extend(schema_errors(item, child, document, location + "." + key))
    elif isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append((location, "数组项数不足"))
        if schema.get("uniqueItems"):
            encoded = [json.dumps(v, sort_keys=True, ensure_ascii=False) for v in value]
            if len(set(encoded)) != len(encoded):
                errors.append((location, "数组含重复项"))
        if "items" in schema:
            for index, item in enumerate(value):
                errors.extend(schema_errors(item, schema["items"], document,
                                            f"{location}[{index}]"))
    elif isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append((location, "字符串为空或过短"))
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append((location, "字符串不符合规定格式"))
    elif type(value) in (int, float):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append((location, "数值低于允许下限"))
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            errors.append((location, "数值必须大于允许下限"))
    return errors


def visible_runs(runs):
    """Join adjacent text runs within one paragraph, never unrelated objects."""
    result, pending = [], []

    def flush():
        if pending:
            result.append("".join(pending))
            pending.clear()

    for run in runs:
        explicit_break = isinstance(run, dict) and (
            run.get("break") is True or run.get("type") in ("break", "line-break", "br"))
        if explicit_break:
            flush()
        elif isinstance(run, dict) and isinstance(run.get("text"), str):
            # Preserve newlines literally; ignore the run's formatting fields.
            pending.append(run["text"])
        else:
            flush()
            result.extend(visible_text(run, rich_context=True))
    flush()
    return result


def visible_text(value, rich_context=False):
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [text for item in value for text in visible_text(item, rich_context)]
    if isinstance(value, dict):
        hidden = {"fact_id", "fact_ids", "asset_id", "asset_ids", "source_id",
                  "source_refs", "source_locators", "speaker_notes", "notes", "metadata"}
        if rich_context or isinstance(value.get("runs"), list):
            hidden.update({"style", "styles", "format", "formatting"})
        result = []
        for key, item in value.items():
            if key not in hidden:
                result.extend(visible_runs(item) if key == "runs" and isinstance(item, list)
                              else visible_text(item, rich_context))
        return result
    return []


class Audit:
    def __init__(self, root, final, check_files):
        self.root, self.final, self.check_files = root, final, check_files
        self.errors, self.warnings = [], []
        self.used_facts, self.used_assets = set(), set()

    def add(self, code, location, message, error=False):
        (self.errors if error else self.warnings).append(
            {"code": code, "location": location, "message": message})

    def index(self, rows, location):
        result = {}
        for row in rows:
            if row["id"] in result:
                self.add("duplicate_id", location, "重复ID: " + row["id"], True)
            else:
                result[row["id"]] = row
        return result

    def refs(self, ids, index, location):
        for identity in ids:
            if identity not in index:
                self.add("broken_reference", location, "引用不存在: " + identity, True)

    def path(self, value, location, used=False):
        if value is None or not value.strip():
            self.add("missing_path", location, "尚无本地文件路径", self.final and used)
            return
        try:
            path = contained(self.root, value)
        except InputError as exc:
            self.add("unsafe_path", location, str(exc), True)
            return
        if self.check_files and not path.is_file():
            self.add("missing_file", location, "本地文件不存在: " + value,
                     self.final and used)
        return path

    def asset_fingerprint(self, path, expected, location, used):
        """Check an optional recorded identity without making hashes mandatory."""
        if not self.check_files or path is None or expected is None:
            return
        try:
            if not path.is_file():
                return  # Missing-file reporting belongs to path().
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != expected.lower():
                self.add("asset_hash_mismatch", location,
                         "素材文件与记录的sha256不一致；需核对文件及既有审阅记录",
                         self.final and used)
        except OSError as exc:
            self.add("asset_hash_unreadable", location,
                     "无法读取素材以核对sha256: " + str(exc), self.final and used)

    def cycles(self, graph, location):
        state = {}
        for start in graph:
            if state.get(start):
                continue
            stack = [(start, iter(graph[start]))]
            state[start] = 1
            while stack:
                node, children = stack[-1]
                child = next(children, None)
                if child is None:
                    state[node] = 2
                    stack.pop()
                elif child in graph and state.get(child) == 1:
                    self.add("dependency_cycle", location,
                             f"检测到循环边: {node} → {child}", True)
                elif child in graph and not state.get(child):
                    state[child] = 1
                    stack.append((child, iter(graph[child])))

    def closure(self, ids, index, field):
        pending, result = list(ids), set()
        while pending:
            identity = pending.pop()
            if identity not in result:
                result.add(identity)
                pending.extend(index.get(identity, {}).get(field, []))
        return result

    def fact_closure(self, ids, asset_ids=()):
        pending = list(ids)
        for aid in self.closure(asset_ids, self.assets, "derived_from"):
            pending.extend(self.assets.get(aid, {}).get("fact_ids", []))
        return self.closure(pending, self.facts, "input_fact_ids")

    def source_refs(self, refs, location, used):
        self.refs([ref["source_id"] for ref in refs], self.sources, location)
        for ref in refs:
            source = self.sources.get(ref["source_id"], {})
            if ref["relation"] == "supports" and source.get("read_scope") == "unread":
                self.add("unread_support", location,
                         "未阅读来源被标为支持: " + ref["source_id"], self.final and used)

    def exceptions(self, row, fact_ids, visible, location):
        exceptions = {}
        for item in row["evidence_exceptions"]:
            fid = item["fact_id"]
            self.refs([fid], self.facts, location + ".evidence_exceptions")
            if fid in exceptions:
                self.add("duplicate_exception", location, "重复事实例外: " + fid, True)
            exceptions[fid] = item
            if fid not in fact_ids:
                self.add("unused_exception", location, "例外未对应本处使用事实: " + fid)
            if not any(item["visible_note"].strip() in text for text in visible):
                self.add("invisible_exception", location,
                         "限定语未出现在可见正文中: " + fid, self.final and fid in fact_ids)
        for fid in fact_ids:
            fact = self.facts.get(fid)
            if not fact:
                continue
            allowed = ({"hypothetical"} if fact["type"] == "assumption" else
                       {"qualified", "hypothetical"} if fact["state"] == "unverified" else
                       {fact["state"]} if fact["state"] in ("qualified", "disputed") else set())
            item = exceptions.get(fid)
            if allowed and (not item or item["treatment"] not in allowed):
                self.add("missing_or_wrong_treatment", location,
                         f"{fid}需要可见例外处理: {', '.join(sorted(allowed))}", self.final)
            elif item and not allowed:
                self.add("unneeded_exception", location,
                         "已支持的非假设事实有额外例外，请核对状态: " + fid)

    def facts_and_assets(self):
        for fid, fact in self.facts.items():
            loc, used = "facts." + fid, fid in self.used_facts
            self.refs(fact["input_fact_ids"], self.facts, loc + ".input_fact_ids")
            self.source_refs(fact["source_refs"], loc + ".source_refs", used)
            support = any(r["relation"] == "supports" for r in fact["source_refs"])
            if fact["type"] == "observation" and not support:
                self.add("no_supporting_source", loc, "观察事实没有supports来源",
                         self.final and used and fact["state"] == "supported")
            if fact["type"] == "derived":
                if not fact["input_fact_ids"] or not fact.get("calculation"):
                    self.add("incomplete_derivation", loc, "派生事实缺输入事实或计算记录",
                             self.final and used)
                if not fact.get("calculation", {}).get("checked"):
                    self.add("calculation_unchecked", loc, "计算未记录为已复算；未执行表达式",
                             self.final and used)
            inherited = [dep for dep in self.fact_closure(fact["input_fact_ids"])
                         if dep in self.facts and (self.facts[dep]["type"] == "assumption"
                         or self.facts[dep]["state"] != "supported")]
            if fact["state"] == "supported" and inherited:
                self.add("qualified_dependency", loc,
                         "支持状态依赖假设或有限证据，应保留条件: " + ", ".join(sorted(inherited)))
            if fact["type"] == "interpretation" and (
                    not (fact["input_fact_ids"] or support) or not fact.get("reasoning", "").strip()):
                self.add("incomplete_reasoning", loc, "解释缺前提或推理记录", self.final and used)
            if fact["state"] in ("qualified", "disputed") and not fact.get("qualification", "").strip():
                self.add("missing_qualification", loc, "缺具体限制或冲突说明", self.final and used)
            if not used and (fact["state"] != "supported" or fact["type"] == "assumption"):
                self.add("unused_evidence_gap", loc, "未使用的证据缺口或假设，仅提示")
        for aid, asset in self.assets.items():
            loc, used = "assets." + aid, aid in self.used_assets
            self.refs(asset["fact_ids"], self.facts, loc + ".fact_ids")
            self.refs(asset.get("derived_from", []), self.assets, loc + ".derived_from")
            self.source_refs(asset["source_refs"], loc + ".source_refs", aid in self.evidence_assets)
            if asset["kind"] == "generated-concept" and asset["truth_role"] == "evidence":
                self.add("generated_as_evidence", loc, "生成概念图不能标为技术事实证据", True)
            if asset["truth_role"] == "evidence":
                provenance = [self.assets[parent] for parent in
                              self.closure([aid], self.assets, "derived_from")
                              if parent in self.assets]
                has_basis = any(item["fact_ids"] or any(
                    ref["relation"] == "supports" for ref in item["source_refs"])
                    for item in provenance)
                if not has_basis:
                    self.add("untraceable_evidence_asset", loc,
                             "证据素材及其派生来源均无支持性来源或事实依据",
                             self.final and used)
            if asset["review_status"] != "reviewed":
                self.add("asset_not_ready", loc, "素材状态: " + asset["review_status"], self.final and used)
            path = self.path(asset["local_path"], loc + ".local_path", used)
            self.asset_fingerprint(path, asset.get("sha256"), loc + ".sha256", used)

    def pages(self, deck):
        pages = self.index(deck["pages"], "deck.pages")
        for pid, page in pages.items():
            loc = "pages." + pid
            if deck.get("notes_enabled", True) and not page["speaker_notes"].strip():
                self.add("missing_speaker_notes", loc + ".speaker_notes",
                         "备注已启用但口语稿为空", self.final)
            self.refs(page["fact_ids"], self.facts, loc + ".fact_ids")
            self.refs(page["asset_ids"], self.assets, loc + ".asset_ids")
            self.refs(page["author_explainer_refs"], self.sections, loc + ".author_explainer_refs")
            for cid in page["author_explainer_refs"]:
                if cid in self.sections and self.sections[cid]["deliverable"] != "author-explainer":
                    self.add("wrong_author_reference", loc, "作者解析引用不是author-explainer: " + cid, True)
            blocks = self.index(page["blocks"], loc + ".blocks")
            self.refs(page["reading_path"], blocks, loc + ".reading_path")
            if not page["reading_path"]:
                self.add("empty_reading_path", loc, "阅读路径为空")
            for bid, block in blocks.items():
                place = loc + "/" + bid
                for field, index in (("fact_ids", self.facts), ("asset_ids", self.assets)):
                    self.refs(block[field], index, place + "." + field)
                    if not set(block[field]).issubset(page[field]):
                        self.add("page_coverage", place, "块级" + field + "未由页级覆盖", True)
                nested = [block["content"]]
                while nested:
                    item = nested.pop()
                    if isinstance(item, list):
                        nested.extend(item)
                    elif isinstance(item, dict):
                        if "fact_id" in item:
                            fid = item["fact_id"]
                            if not isinstance(fid, str) or fid not in self.facts:
                                self.add("cell_fact_reference", place, "内容内fact_id无效或不存在", True)
                            elif fid not in block["fact_ids"]:
                                self.add("cell_fact_coverage", place, "内容内fact_id未由块级覆盖: " + fid, True)
                        nested.extend(item.values())
                geom = block.get("geometry")
                # Ignore only arithmetic roundoff in pt coordinates, not visible overflow.
                epsilon = 1e-7
                if geom and (geom["x"] < -epsilon or geom["y"] < -epsilon or
                             geom["x"] + geom["w"] > deck["canvas"]["width_pt"] + epsilon or
                             geom["y"] + geom["h"] > deck["canvas"]["height_pt"] + epsilon):
                    self.add("planned_bounds", place, "计划pt矩形超出画布；不代表像素检测", True)
                key = "table_min_pt" if block["kind"] == "table" else "body_min_pt"
                minimum = page["density"].get(key)
                if minimum and block.get("font_pt", minimum) < minimum:
                    self.add("small_declared_font", place, f"计划字号低于本页声明的{key}={minimum}")
            effective = self.fact_closure(page["fact_ids"], page["asset_ids"])
            visible = [page["title"]] + [text for b in page["blocks"] for text in visible_text(b["content"])]
            self.exceptions(page, effective, visible, loc)
        self.engine_map(deck["engine_map"], pages)

    def engine_map(self, rows, pages):
        if not rows and self.final:
            self.add("missing_engine_map", "engine_map", "最终计划没有制作映射；不证明编辑性通过")
        mapped, slots = set(), set()
        page_order = {pid: order for order, pid in enumerate(pages)}
        output_pages = {}
        for i, row in enumerate(rows):
            loc = f"engine_map[{i}]"
            self.refs([row["page_id"]], pages, loc)
            output = self.path(row["output_path"], loc + ".output_path", True)
            slot = (output or row["output_path"], row["slide_number"])
            if slot in slots:
                self.add("duplicate_slide_mapping", loc, "同一输出文件的页码重复映射", True)
            slots.add(slot)
            mapped.add(row["page_id"])
            page = pages.get(row["page_id"])
            if page:
                blocks = {b["id"]: b for b in page["blocks"]}
                self.refs(row["object_ids"], blocks, loc + ".object_ids")
                self.refs([obj["block_id"] for obj in row.get("actual_objects", [])],
                          blocks, loc + ".actual_objects")
                if self.final:
                    output_pages.setdefault(slot[0], []).append(
                        (row["slide_number"], row["page_id"], loc))
                    if any(row["object_ids"].values()):
                        missing = [bid for bid in blocks if not row["object_ids"].get(bid)]
                        if missing:
                            self.add("unmapped_block", loc + ".object_ids",
                                     "部分内容块无可靠对象映射，需逐块对照成品: " + ", ".join(missing))
            for field, index in (("fact_id_map", self.facts), ("source_id_map", self.sources),
                                 ("asset_path_map", self.assets)):
                self.refs(row.get(field, {}), index, loc + "." + field)
            for aid, value in row.get("asset_path_map", {}).items():
                self.path(value, loc + ".asset_path_map." + aid, aid in self.used_assets)
            if self.final and not any(row["object_ids"].values()):
                self.add("missing_object_mapping", loc, "尚无可靠对象ID映射；不证明编辑性通过")
        if rows and self.final:
            for pid in pages.keys() - mapped:
                self.add("unmapped_page", "engine_map", "页面无制作映射: " + pid)
            for output, entries in output_pages.items():
                seen = set()
                ordered = []
                for slide, pid, loc in sorted(entries, key=lambda entry: entry[0]):
                    if pid in seen:
                        self.add("repeated_page_mapping", loc,
                                 "同一计划页在同一输出文件重复映射，需核对重复/拆页去向: " + pid)
                    seen.add(pid)
                    ordered.append(pid)
                positions = [page_order[pid] for pid in ordered]
                if positions != sorted(positions):
                    self.add("page_order_mismatch", "engine_map",
                             "声明的输出页序与deck.pages不同，需同步计划或记录有意重排: "
                             + str(output) + " → " + ", ".join(ordered))

    def run(self, ledger, deck, ledger_path):
        self.sources = self.index(ledger["sources"], "sources")
        self.facts = self.index(ledger["facts"], "facts")
        self.assets = self.index(ledger["assets"], "assets")
        self.sections = self.index(ledger["sections"], "sections")
        consumers = ledger["sections"] + (deck["pages"] if deck else [])
        for row in consumers:
            self.used_assets.update(row["asset_ids"])
            self.used_facts.update(self.fact_closure(row["fact_ids"], row["asset_ids"]))
        self.evidence_assets = self.closure(self.used_assets, self.assets, "derived_from")
        for sid, source in self.sources.items():
            if source.get("parent_source_id") is not None:
                self.refs([source["parent_source_id"]], self.sources, "sources." + sid)
        self.cycles({s: [r["parent_source_id"]] if r.get("parent_source_id") is not None else []
                     for s, r in self.sources.items()}, "sources.parent_source_id")
        self.cycles({f: r["input_fact_ids"] for f, r in self.facts.items()}, "facts.input_fact_ids")
        self.cycles({a: r.get("derived_from", []) for a, r in self.assets.items()}, "assets.derived_from")
        self.cycles({c: r["depends_on"] for c, r in self.sections.items()}, "sections.depends_on")
        self.facts_and_assets()
        for cid, section in self.sections.items():
            loc = "sections." + cid
            for field, index in (("fact_ids", self.facts), ("asset_ids", self.assets), ("depends_on", self.sections)):
                self.refs(section[field], index, loc + "." + field)
            self.exceptions(section, self.fact_closure(section["fact_ids"], section["asset_ids"]),
                            [section["body"]], loc)
        if deck:
            if contained(self.root, deck["source_ledger"]) != ledger_path:
                self.add("ledger_mismatch", "deck.source_ledger", "指向的账本与--ledger不一致", True)
            self.pages(deck)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise InputError(message)


def main():
    hashes = {}
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        parser = Parser(description=__doc__)
        parser.add_argument("--root", required=True)
        parser.add_argument("--ledger", required=True)
        parser.add_argument("--deck")
        parser.add_argument("--stage", choices=("draft", "final"), default="draft")
        parser.add_argument("--check-files", action="store_true")
        args = parser.parse_args()
        root = Path(args.root).resolve()
        if not root.is_dir():
            raise InputError("root不是可读项目目录")
        ledger_path = contained(root, args.ledger)
        ledger, hashes["ledger"] = read_json(ledger_path)
        deck = None
        if args.deck:
            deck, hashes["deck"] = read_json(contained(root, args.deck))
        audit = Audit(root, args.stage == "final", args.check_files)
        schema_dir = Path(__file__).resolve().parent.parent / "assets"
        for name, data, filename in (("ledger", ledger, "content-ledger.schema.json"),
                                     ("deck", deck, "deck-plan.schema.json")):
            if name == "deck" and not args.deck:
                continue
            schema, _ = read_json(schema_dir / filename)
            for location, message in schema_errors(data, schema, schema, name):
                audit.add("structure", location, message, True)
        if not audit.errors:
            audit.run(ledger, deck, ledger_path)
        result = {"status": "errors" if audit.errors else "no_structural_errors", "stage": args.stage,
                  "errors": audit.errors, "warnings": audit.warnings,
                  "limits": LIMITS, "sourcehash": hashes}
        code = 1 if audit.errors else 0
    except (InputError, OSError, ValueError, RecursionError, RuntimeError,
            KeyError, TypeError, AttributeError, re.error) as exc:
        result = {"status": "input_error", "errors": [{"code": "input", "message": str(exc)}],
                  "warnings": [], "limits": LIMITS, "sourcehash": hashes}
        code = 2
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
