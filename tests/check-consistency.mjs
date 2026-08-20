#!/usr/bin/env node

/**
 * Static consistency checker for moon-skills workflow harness.
 *
 * Validates:
 * 1. Artifact chain — upstream outputs referenced in downstream preconditions
 * 2. Route targets — every "next step" skill actually exists
 * 3. Single ownership — TB/AC/TC/EV/ADR each owned by exactly one skill
 * 4. Work mode coverage — SDD-chain skills mention all three modes
 * 5. Reference files — all referenced files exist on disk
 * 6. Immune governance cycle — schema, write-back, decay fields consistent
 * 7. Uncertainty protocol — two-stage cleanup referenced in sync-context and audit
 * 8. Prompt files — prompts/ directory contains expected scenario files
 * 9. Frontend SDD chain — seams that break silently when several people edit in parallel
 */

import { readFileSync, readdirSync, existsSync } from "fs";
import { join, resolve } from "path";

const ROOT = resolve(import.meta.dirname, "..");
const SKILLS_DIR = join(ROOT, "skills");

const PASS = "\x1b[32mPASS\x1b[0m";
const FAIL = "\x1b[31mFAIL\x1b[0m";
const WARN = "\x1b[33mWARN\x1b[0m";

let totalPass = 0;
let totalFail = 0;
let totalWarn = 0;

function report(level, rule, detail) {
  const tag = level === "pass" ? PASS : level === "fail" ? FAIL : WARN;
  console.log(`  [${tag}] ${rule}: ${detail}`);
  if (level === "pass") totalPass++;
  else if (level === "fail") totalFail++;
  else totalWarn++;
}

function readSkill(name) {
  const path = join(SKILLS_DIR, name, "SKILL.md");
  if (!existsSync(path)) return null;
  return readFileSync(path, "utf-8");
}

function allSkillNames() {
  return readdirSync(SKILLS_DIR, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => d.name)
    .filter((name) => existsSync(join(SKILLS_DIR, name, "SKILL.md")));
}

// ── 1. Artifact chain ──────────────────────────────────────────────

const ARTIFACT_CHAIN = [
  {
    producer: "analysis-spec",
    artifact: "analysis-spec.md",
    consumers: ["design-pack", "slice-plan"],
  },
  {
    producer: "design-pack",
    artifact: "design-pack.md",
    consumers: ["slice-plan", "verify"],
  },
  {
    producer: "slice-plan",
    artifact: "slice-plan.md",
    consumers: ["code-review", "verify"],
  },
  {
    producer: "code-review",
    artifact: "code-review.md",
    consumers: [],
  },
  {
    producer: "verify",
    artifact: "verify.md",
    consumers: ["spec-check"],
  },
];

function checkArtifactChain() {
  console.log("\n── 1. Artifact Chain ──");
  for (const { producer, artifact, consumers } of ARTIFACT_CHAIN) {
    const producerContent = readSkill(producer);
    if (!producerContent) {
      report("fail", "artifact-chain", `${producer}/SKILL.md not found`);
      continue;
    }
    if (!producerContent.includes(artifact)) {
      report(
        "fail",
        "artifact-chain",
        `${producer} does not mention its artifact "${artifact}"`
      );
    }
    for (const consumer of consumers) {
      const content = readSkill(consumer);
      if (!content) {
        report("fail", "artifact-chain", `${consumer}/SKILL.md not found`);
        continue;
      }
      if (content.includes(artifact)) {
        report(
          "pass",
          "artifact-chain",
          `${consumer} references "${artifact}" from ${producer}`
        );
      } else {
        report(
          "fail",
          "artifact-chain",
          `${consumer} does NOT reference "${artifact}" (produced by ${producer})`
        );
      }
    }
  }
}

// ── 2. Route targets ───────────────────────────────────────────────

const KNOWN_EXTERNAL = ["superpowers:systematic-debugging"];

function checkRouteTargets() {
  console.log("\n── 2. Route Targets ──");
  const skillNames = allSkillNames();
  const skillRefs = new Set();

  for (const name of skillNames) {
    const content = readSkill(name);
    const backtickRefs = content.match(/`([a-z][\w-]*)`/g) || [];
    for (const ref of backtickRefs) {
      const clean = ref.replace(/`/g, "");
      if (
        skillNames.includes(clean) ||
        KNOWN_EXTERNAL.some((e) => e.includes(clean))
      ) {
        skillRefs.add(`${name} -> ${clean}`);
      }
    }
  }

  for (const name of skillNames) {
    const content = readSkill(name);
    const nextSection = content.match(
      /### 下一步[\s\S]*?(?=\n##[^#]|\n---|\Z)/
    );
    if (!nextSection) continue;

    const targets =
      nextSection[0].match(/`([a-z][\w-]*)`/g)?.map((r) => r.replace(/`/g, "")) || [];
    for (const target of targets) {
      if (KNOWN_EXTERNAL.includes(target)) {
        report(
          "pass",
          "route-target",
          `${name} → ${target} (external, acknowledged)`
        );
        continue;
      }
      if (skillNames.includes(target)) {
        report("pass", "route-target", `${name} → ${target} exists`);
      } else if (
        [
          "analysis-spec",
          "design-pack",
          "slice-plan",
          "verify",
          "spec-check",
          "audit",
          "sync-context",
          "initialize",
          "immune-debug",
        ].includes(target)
      ) {
        if (!existsSync(join(SKILLS_DIR, target, "SKILL.md"))) {
          report(
            "fail",
            "route-target",
            `${name} → ${target} referenced but SKILL.md not found`
          );
        }
      }
    }
  }
}

// ── 3. Single ownership ────────────────────────────────────────────

const OWNERSHIP = {
  TB: { owner: "analysis-spec", label: "Target Behavior" },
  AC: { owner: "design-pack", label: "Acceptance Criteria" },
  TC: { owner: "design-pack", label: "Test Case" },
  EV: { owner: "verify", label: "Evidence" },
  ADR: { owner: "design-pack", label: "Architecture Decision Record" },
};

function checkSingleOwnership() {
  console.log("\n── 3. Single Ownership (TB/AC/TC/EV/ADR) ──");
  const skillNames = allSkillNames();

  for (const [abbr, { owner, label }] of Object.entries(OWNERSHIP)) {
    const producerPattern = new RegExp(
      `产出.*${abbr}|定义.*${abbr}|生成.*${abbr}`,
      "i"
    );
    for (const name of skillNames) {
      if (name === owner) continue;
      const content = readSkill(name);
      const artifactSection = content.match(
        /## 工件管理[\s\S]*?(?=\n##[^#]|\n---|\Z)/
      );
      if (
        artifactSection &&
        artifactSection[0].match(
          new RegExp(`\\b${abbr}\\b.*产出|产出.*\\b${abbr}\\b`)
        )
      ) {
        report(
          "fail",
          "single-ownership",
          `${name} claims to produce ${abbr} (${label}), but owner is ${owner}`
        );
      }
    }
    report(
      "pass",
      "single-ownership",
      `${abbr} (${label}) — owner: ${owner}`
    );
  }
}

// ── 4. Work mode coverage ──────────────────────────────────────────

const SDD_CHAIN_SKILLS = [
  "analysis-spec",
  "design-pack",
  "slice-plan",
  "code-review",
  "verify",
  "spec-check",
  "audit",
];
const WORK_MODES = ["patch-lite", "feature-slice", "migration-strict"];

function checkWorkModeCoverage() {
  console.log("\n── 4. Work Mode Coverage ──");
  for (const name of SDD_CHAIN_SKILLS) {
    const content = readSkill(name);
    if (!content) {
      report("fail", "work-mode", `${name}/SKILL.md not found`);
      continue;
    }
    const missing = WORK_MODES.filter((mode) => !content.includes(mode));
    if (missing.length === 0) {
      report("pass", "work-mode", `${name} covers all 3 modes`);
    } else if (missing.length === 3) {
      report(
        "warn",
        "work-mode",
        `${name} mentions NONE of the 3 modes (may be intentional for audit/spec-check)`
      );
    } else {
      report(
        "warn",
        "work-mode",
        `${name} missing: ${missing.join(", ")}`
      );
    }
  }
}

// ── 5. Reference files ─────────────────────────────────────────────

const REFERENCE_CHECKS = [
  {
    skill: "analysis-spec",
    files: [
      "references/frontend-lens.md",
      "references/backend-lens.md",
      "references/integration-lens.md",
      "references/risk-memory-lens.md",
      "references/lens-template.md",
    ],
  },
  {
    skill: "verify",
    files: [
      "references/frontend-verify-pack.md",
      "references/backend-verify-pack.md",
      "references/integration-verify-pack.md",
    ],
  },
  {
    skill: "design-pack",
    files: ["references/design-pack-template.md"],
  },
  {
    skill: "code-review",
    files: ["references/review-rules-template.md"],
  },
  {
    skill: "immune-debug",
    files: [
      "references/immune-decision-matrix.md",
      "references/immune-registry-schema.md",
      "references/examples.md",
    ],
  },
  {
    skill: "session-optimize",
    files: ["references/failure-map.md", "references/learnings-ledger.md"],
  },
];

function checkReferenceFiles() {
  console.log("\n── 5. Reference Files ──");
  for (const { skill, files } of REFERENCE_CHECKS) {
    for (const file of files) {
      const fullPath = join(SKILLS_DIR, skill, file);
      if (existsSync(fullPath)) {
        report("pass", "reference-file", `${skill}/${file} exists`);
      } else {
        report("fail", "reference-file", `${skill}/${file} NOT FOUND`);
      }
    }
  }
}

// ── 6. Immune governance cycle ─────────────────────────────────────

const IMMUNE_FIELDS = [
  "added_at",
  "last_checked_at",
  "last_triggered_at",
  "defensive_rule_id",
  "governance_tags",
];

const IMMUNE_CYCLE = [
  {
    skill: "immune-debug",
    role: "writer",
    requiredFields: ["added_at", "last_checked_at", "last_triggered_at", "defensive_rule_id", "governance_tags"],
    requiredTerms: ["immune-registry.yaml"],
  },
  {
    skill: "code-review",
    role: "write-back",
    requiredFields: ["last_checked_at", "last_triggered_at", "defensive_rule_id"],
    requiredTerms: ["immune-registry.yaml", "defensive"],
  },
  {
    skill: "audit",
    role: "decay",
    requiredFields: ["last_checked_at", "governance_tags", "needs-review"],
    requiredTerms: ["immune-registry.yaml", "Freshness Check"],
  },
];

function checkImmuneGovernance() {
  console.log("\n── 6. Immune Governance Cycle ──");

  const schemaPath = join(SKILLS_DIR, "immune-debug", "references", "immune-registry-schema.md");
  if (existsSync(schemaPath)) {
    const schema = readFileSync(schemaPath, "utf-8");
    for (const field of IMMUNE_FIELDS) {
      if (schema.includes(field)) {
        report("pass", "immune-schema", `Schema defines "${field}"`);
      } else {
        report("fail", "immune-schema", `Schema missing field "${field}"`);
      }
    }
  } else {
    report("fail", "immune-schema", "immune-registry-schema.md NOT FOUND");
  }

  for (const { skill, role, requiredFields, requiredTerms } of IMMUNE_CYCLE) {
    const content = readSkill(skill);
    if (!content) {
      report("fail", "immune-cycle", `${skill}/SKILL.md not found`);
      continue;
    }
    for (const field of requiredFields) {
      if (content.includes(field)) {
        report("pass", "immune-cycle", `${skill} (${role}) mentions "${field}"`);
      } else {
        report("fail", "immune-cycle", `${skill} (${role}) missing "${field}"`);
      }
    }
    for (const term of requiredTerms) {
      if (content.includes(term)) {
        report("pass", "immune-cycle", `${skill} (${role}) mentions "${term}"`);
      } else {
        report("fail", "immune-cycle", `${skill} (${role}) missing "${term}"`);
      }
    }
  }

  const reviewTemplate = readFileSync(
    join(SKILLS_DIR, "code-review", "references", "review-rules-template.md"),
    "utf-8"
  );
  if (reviewTemplate.includes("immune_ref") && reviewTemplate.includes("DEF-R-")) {
    report("pass", "immune-cycle", "review-rules-template has immune_ref + DEF-R-N format");
  } else {
    report("fail", "immune-cycle", "review-rules-template missing immune_ref or DEF-R-N format");
  }

  const decisionMatrix = readFileSync(
    join(SKILLS_DIR, "immune-debug", "references", "immune-decision-matrix.md"),
    "utf-8"
  );
  if (decisionMatrix.includes("immune-registry-schema.md")) {
    report("pass", "immune-cycle", "decision-matrix references schema doc");
  } else {
    report("fail", "immune-cycle", "decision-matrix does NOT reference schema doc");
  }
}

// ── 7. Uncertainty protocol ───────────────────────────────────────

function checkUncertaintyProtocol() {
  console.log("\n── 7. Uncertainty Protocol ──");
  const REQUIRED = [
    { skill: "sync-context", terms: ["possibly-resolved", "uncertainty"] },
    { skill: "audit", terms: ["possibly-resolved"] },
  ];

  for (const { skill, terms } of REQUIRED) {
    const content = readSkill(skill);
    if (!content) {
      report("fail", "uncertainty", `${skill}/SKILL.md not found`);
      continue;
    }
    for (const term of terms) {
      if (content.includes(term)) {
        report("pass", "uncertainty", `${skill} mentions "${term}"`);
      } else {
        report("fail", "uncertainty", `${skill} missing "${term}"`);
      }
    }
  }

  const syncContent = readSkill("sync-context");
  if (syncContent && syncContent.includes("不要直接移除 uncertainty")) {
    report("pass", "uncertainty", "sync-context has hard gate against direct removal");
  } else {
    report("fail", "uncertainty", "sync-context missing hard gate against direct removal");
  }
}

// ── 8. Prompt files ───────────────────────────────────────────────

const EXPECTED_PROMPTS = ["troubleshoot.md", "onboarding.md", "review-immune.md"];

function checkPromptFiles() {
  console.log("\n── 8. Prompt Files ──");
  const promptsDir = join(ROOT, "prompts");
  if (!existsSync(promptsDir)) {
    report("fail", "prompts", "prompts/ directory NOT FOUND");
    return;
  }
  for (const file of EXPECTED_PROMPTS) {
    const fullPath = join(promptsDir, file);
    if (existsSync(fullPath)) {
      report("pass", "prompts", `prompts/${file} exists`);
    } else {
      report("fail", "prompts", `prompts/${file} NOT FOUND`);
    }
  }
}

// ── 9. Frontend SDD chain ─────────────────────────────────────────
//
// Seams listed in docs/skills/frontend-sdd/接缝契约.md. Each check here
// catches a drift that is invisible at review time but breaks the agent
// at run time.

const FRONTEND_ROOTS = [
  join(SKILLS_DIR, "sdd-dev-frontend"),
  join(SKILLS_DIR, "sdd-init-frontend"),
  join(SKILLS_DIR, "sdd-task-frontend"),
  join(ROOT, "docs", "skills", "frontend-sdd"),
];

// Namespaces registered in docs/skills/frontend-sdd/接缝契约.md §2. The registry
// itself is skipped when scanning, since it necessarily names every prefix.
// 与 接缝契约.md §2 的注册表保持一致；加前缀两处都要改。
const ID_REGISTRY = join("frontend-sdd", "接缝契约.md");
const ID_REGISTRY_PATH = join(ROOT, "docs", "skills", ID_REGISTRY);

// 标准名，形状上撞 ID 规则但不是命名空间（SHA-256 / ISO-8601）。
// 它们刻意不在 接缝契约 §2 登记，所以只能列在这里。
const NON_ID_PREFIXES = ["SHA", "ISO"];

// 前缀白名单从 接缝契约 §2 的表格现读，不再在此复制一份。
// 复制过一份，结果两处漂移：曾有 7 个前缀只在代码里、不在表里。
function readRegisteredIdPrefixes() {
  const content = readFileSync(ID_REGISTRY_PATH, "utf-8");
  const section = content.split(/^### 2\. /m)[1]?.split(/^### /m)[0];
  if (!section) return null;
  const prefixes = new Set(NON_ID_PREFIXES);
  for (const line of section.split("\n")) {
    if (!line.startsWith("|")) continue;
    const firstCell = line.split("|")[1] ?? "";
    for (const token of firstCell.matchAll(/`([^`]+)`/g)) {
      // 只取命名空间段：`REQ-DEC-*` 登记 REQ，`REG` 这类无后缀的整体登记。
      const withSuffix = token[1].match(/^([A-Z]{2,10})-/);
      if (withSuffix) prefixes.add(withSuffix[1]);
      else if (/^[A-Z]{2,10}$/.test(token[1])) prefixes.add(token[1]);
    }
  }
  return prefixes;
}

const AGENT_SECTIONS = ["前置", "只读", "输出格式"];

const OWNED_SCRIPTS = [
  "extract_design_spec.py",
  "verify_restore_contract.py",
  "collect_restore_facts.js",
  "manage_repo_baseline.py",
  "manage_execution_evidence.py",
  "manage_review_pipeline.py",
];

function walkMarkdown(dir) {
  if (!existsSync(dir)) return [];
  const out = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === "__pycache__" || entry.name === "node_modules") continue;
      out.push(...walkMarkdown(full));
    } else if (entry.name.endsWith(".md")) {
      out.push(full);
    }
  }
  return out;
}

function slugify(heading) {
  return heading
    .replace(/[`*]/g, "")
    .replace(/[^A-Za-z0-9_\u4e00-\u9fff -]/g, "")
    .trim()
    .toLowerCase()
    .replace(/ /g, "-");
}

function headingSlugs(content) {
  const slugs = new Set();
  for (const line of content.split("\n")) {
    const m = line.match(/^#{1,6}\s+(.*)$/);
    if (m) slugs.add(slugify(m[1].trim()));
  }
  return slugs;
}

function rel(path) {
  return path.slice(ROOT.length + 1);
}

function checkFrontendLinks(files) {
  const slugCache = new Map();
  let checked = 0;
  let failed = 0;

  for (const file of files) {
    const content = readFileSync(file, "utf-8");
    const dir = resolve(file, "..");
    for (const match of content.matchAll(/\]\(([^)\s]+)\)/g)) {
      const link = match[1];
      if (/^(https?:|mailto:)/.test(link)) continue;
      const [pathPart, anchor] = link.split("#");
      const target = pathPart ? resolve(dir, pathPart) : file;
      checked++;
      if (!existsSync(target)) {
        report("fail", "fe-link", `${rel(file)} → ${link} (target not found)`);
        failed++;
        continue;
      }
      if (!anchor || !target.endsWith(".md")) continue;
      if (!slugCache.has(target)) {
        slugCache.set(target, headingSlugs(readFileSync(target, "utf-8")));
      }
      if (!slugCache.get(target).has(slugify(anchor))) {
        report("fail", "fe-link", `${rel(file)} → ${link} (anchor not found)`);
        failed++;
      }
    }
  }
  if (failed === 0) {
    report("pass", "fe-link", `${checked} links and anchors all resolve`);
  }
}

function checkFrontendPathVariables(files) {
  const skillPath = join(SKILLS_DIR, "sdd-dev-frontend", "SKILL.md");
  const skill = readFileSync(skillPath, "utf-8");
  const defined = new Set(
    [...skill.matchAll(/\|\s*`(<[a-z0-9-]+>)`/g)].map((m) => m[1])
  );
  const used = new Map();

  for (const file of files) {
    const content = readFileSync(file, "utf-8");
    for (const m of content.matchAll(/<[a-z][a-z0-9-]*-(?:dir|ref|root|driver|id)>/g)) {
      if (!used.has(m[0])) used.set(m[0], new Set());
      used.get(m[0]).add(rel(file));
    }
  }

  let failed = 0;
  for (const [variable, where] of used) {
    if (!defined.has(variable)) {
      report(
        "fail",
        "fe-path-var",
        `${variable} used in ${[...where].join(", ")} but not defined in SKILL.md 路径变量`
      );
      failed++;
    }
  }
  if (failed === 0) {
    report("pass", "fe-path-var", `${used.size} path variables all defined`);
  }
}

function checkFrontendGateNumbers(files) {
  const skill = readFileSync(join(SKILLS_DIR, "sdd-dev-frontend", "SKILL.md"), "utf-8");

  const hardSection = skill.split("## 硬门禁")[1]?.split("\n## ")[0] ?? "";
  const hardGates = new Set(
    [...hardSection.matchAll(/^(\d+)\.\s+\*\*/gm)].map((m) => Number(m[1]))
  );
  const exitSection = skill.split("## 退出门禁")[1]?.split("\n## ")[0] ?? "";
  const exitGates = new Set(
    [...exitSection.matchAll(/^\|\s*(\d+)\s*\|/gm)].map((m) => Number(m[1]))
  );

  if (hardGates.size === 0 || exitGates.size === 0) {
    report("fail", "fe-gate", "cannot parse 硬门禁 / 退出门禁 numbering from SKILL.md");
    return;
  }

  let failed = 0;
  for (const file of files) {
    const content = readFileSync(file, "utf-8");
    for (const m of content.matchAll(/硬门禁(?:第)?\s*(\d+)/g)) {
      if (!hardGates.has(Number(m[1]))) {
        report("fail", "fe-gate", `${rel(file)} references 硬门禁 ${m[1]}, which is not defined`);
        failed++;
      }
    }
    for (const m of content.matchAll(/退出门禁(?:的)?第\s*(\d+)\s*条/g)) {
      if (!exitGates.has(Number(m[1]))) {
        report("fail", "fe-gate", `${rel(file)} references 退出门禁第 ${m[1]} 条, which is not defined`);
        failed++;
      }
    }
  }
  if (failed === 0) {
    report(
      "pass",
      "fe-gate",
      `all gate references resolve (硬门禁 ${hardGates.size} 条, 退出门禁 ${exitGates.size} 条)`
    );
  }
}

const ID_COLUMN_HEADERS = ["#", "ID", "编号"];

// A row names a dimension only when its table declares an id column and a
// 「维度」column. Tables like stack-antipatterns' `| 维度 | 具体表现 |` put the
// id itself under 「维度」and must not be read as name declarations.
function dimensionNamesInTables(content) {
  const found = [];
  const lines = content.split("\n");
  let idCol = -1;
  let nameCol = -1;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line.startsWith("|")) {
      idCol = -1;
      nameCol = -1;
      continue;
    }
    const cells = line.split("|").slice(1, -1).map((c) => c.trim());
    if (/^\|[\s|:-]+\|$/.test((lines[i + 1] ?? "").trim())) {
      idCol = cells.findIndex((c) => ID_COLUMN_HEADERS.includes(c));
      nameCol = cells.indexOf("维度");
      continue;
    }
    if (idCol < 0 || nameCol < 0) continue;
    const id = cells[idCol];
    const name = (cells[nameCol] ?? "").replace(/[`*]/g, "").trim();
    if (/^[CQLRF]\d$/.test(id) && name) found.push([id, name]);
  }
  return found;
}

function checkFrontendDimensionNames(files) {
  const names = new Map();

  for (const file of files) {
    const content = readFileSync(file, "utf-8");
    const found = dimensionNamesInTables(content);
    for (const m of content.matchAll(/^#{3,4}\s+([CQLRF]\d)\s+—\s+(.+)$/gm)) {
      found.push([m[1], m[2].replace(/[`*]/g, "").trim()]);
    }
    for (const [id, name] of found) {
      if (!names.has(id)) names.set(id, new Map());
      if (!names.get(id).has(name)) names.get(id).set(name, new Set());
      names.get(id).get(name).add(rel(file));
    }
  }

  let failed = 0;
  for (const [id, variants] of names) {
    if (variants.size > 1) {
      const detail = [...variants]
        .map(([name, where]) => `"${name}" (${[...where].join(", ")})`)
        .join(" vs ");
      report("fail", "fe-dimension", `${id} named inconsistently: ${detail}`);
      failed++;
    }
  }
  if (failed === 0) {
    report("pass", "fe-dimension", `${names.size} dimension ids named consistently`);
  }
}

function checkFrontendIdPrefixes(files) {
  const registered = readRegisteredIdPrefixes();
  // 解析不出来时按失败处理：白名单静默变空会让每个前缀都报错，噪音掩盖真问题。
  if (!registered || registered.size < 10) {
    report(
      "fail",
      "fe-id-prefix",
      `无法从 ${ID_REGISTRY} §2 解析出前缀表（得到 ${registered ? registered.size : 0} 条），检查该节的表格结构`
    );
    return;
  }
  const seen = new Map();
  // Only the leading segment is the namespace: PATTERN-CARD-1 registers PATTERN.
  const idPattern = /(?<![A-Za-z0-9-])([A-Z]{2,10})(?:-[A-Z0-9]{1,12})*-(?:<[nmi]d?>|\d+|\*)/g;
  for (const file of files) {
    if (file.endsWith(ID_REGISTRY)) continue;
    const content = readFileSync(file, "utf-8");
    for (const m of content.matchAll(idPattern)) {
      if (!seen.has(m[1])) seen.set(m[1], new Set());
      seen.get(m[1]).add(rel(file));
    }
  }

  let failed = 0;
  for (const [prefix, where] of seen) {
    if (!registered.has(prefix)) {
      report(
        "fail",
        "fe-id-prefix",
        `${prefix}-* used in ${[...where].join(", ")} but not registered in 接缝契约 §2`
      );
      failed++;
    }
  }
  if (failed === 0) {
    report("pass", "fe-id-prefix", `${seen.size} id prefixes all registered`);
  }
}

function checkFrontendAgentStructure() {
  let failed = 0;
  let count = 0;
  for (const skill of ["sdd-dev-frontend", "sdd-init-frontend"]) {
    const dir = join(SKILLS_DIR, skill, "agents");
    if (!existsSync(dir)) continue;
    for (const file of walkMarkdown(dir)) {
      count++;
      const headings = readFileSync(file, "utf-8")
        .split("\n")
        .filter((line) => /^#{2,3}\s/.test(line))
        .join("\n");
      const missing = AGENT_SECTIONS.filter((section) => !headings.includes(section));
      if (missing.length > 0) {
        report("fail", "fe-agent-shape", `${rel(file)} missing section(s): ${missing.join(", ")}`);
        failed++;
      }
    }
  }
  if (failed === 0) {
    report("pass", "fe-agent-shape", `${count} agent prompts have 前置 / 只读 / 输出格式`);
  }
}

function checkFrontendScriptPaths(files) {
  let failed = 0;
  const pattern = new RegExp(`(\\S{0,60})scripts/(${OWNED_SCRIPTS.join("|")})`, "g");
  for (const file of files) {
    // Governance docs list script filenames as inventory, not as commands.
    if (!file.startsWith(SKILLS_DIR)) continue;
    const content = readFileSync(file, "utf-8");
    for (const m of content.matchAll(pattern)) {
      if (m[1].includes("-dir>/")) continue;
      report(
        "fail",
        "fe-script-path",
        `${rel(file)} has bare "scripts/${m[2]}" — must be prefixed with <skill-dir>/`
      );
      failed++;
    }
  }
  if (failed === 0) {
    report("pass", "fe-script-path", "all script paths qualified with <skill-dir>/");
  }
}

// 一份脚本没有任何提示词再调用它，等于判据从确定性退回散文，而脚本和它的单测
// 还在绿着——瘦身时真出过一次：preflight 缓存的四处调用点被删，命中判据变成
// 提示词里让主 agent 手工比对的一段话。
function checkFrontendScriptOwners(files) {
  // 只认 skills/ 下的提示词与 references：治理文档（docs/skills/frontend-sdd/）列脚本名
  // 是清单，不是调用点。把清单算作调用者，这条检查就永远不会失败了。
  const prose = files
    .filter((file) => file.startsWith(SKILLS_DIR))
    .map((file) => readFileSync(file, "utf-8"))
    .join("\n");
  let failed = 0;
  let count = 0;

  for (const root of FRONTEND_ROOTS) {
    const dir = join(root, "scripts");
    if (!existsSync(dir)) continue;
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      if (!entry.isFile()) continue;
      if (!/\.(py|js|mjs|sh)$/.test(entry.name)) continue;
      count++;
      if (!prose.includes(entry.name)) {
        report(
          "fail",
          "fe-script-owner",
          `${rel(join(dir, entry.name))} is never invoked from any chain Markdown — ` +
            `wire it back into the phase/reference that needs it, or delete script + tests`
        );
        failed++;
      }
    }
  }
  if (failed === 0) {
    report("pass", "fe-script-owner", `${count} scripts all have a calling doc`);
  }
}

// 22 条门禁全是散文，脚本一条都不引用，所以「门禁被遵守了吗」本来无法机械测量。
// evals.json 的 gates 字段建立这条链接：每条门禁至少要有一条情景题断言它。
// KNOWN_UNCOVERED 是棘轮——只许变短。**当前已空，22/22 全覆盖。** 想往里加必须先说明
// 为什么这条门禁不值得测；答不出来通常意味着它根本不该占一个编号。
const KNOWN_UNCOVERED_GATES = new Map([]);

function checkFrontendGateCoverage() {
  const skillPath = join(SKILLS_DIR, "sdd-dev-frontend", "SKILL.md");
  const skill = readFileSync(skillPath, "utf-8");

  const hard = [...skill.matchAll(/^(\d+)\.\s+\*\*/gm)].map((m) => `硬门禁 ${m[1]}`);
  const exitSection = skill.split("## 退出门禁")[1]?.split("\n## ")[0] ?? "";
  const exits = [...exitSection.matchAll(/^\|\s*(\d)\s*\|/gm)].map((m) => `退出门禁 ${m[1]}`);
  const gates = [...hard, ...exits];

  if (hard.length === 0 || exits.length === 0) {
    report("fail", "fe-gate-coverage", "无法从 SKILL.md 解析出门禁清单，检查两节的结构");
    return;
  }

  const evalsPath = join(SKILLS_DIR, "sdd-dev-frontend", "evals", "evals.json");
  const cases = JSON.parse(readFileSync(evalsPath, "utf-8")).evals ?? [];
  const covered = new Set(cases.flatMap((c) => c.gates ?? []));

  let failed = 0;
  for (const gate of gates) {
    if (covered.has(gate)) continue;
    if (KNOWN_UNCOVERED_GATES.has(gate)) continue;
    report(
      "fail",
      "fe-gate-coverage",
      `${gate} 没有任何 evals 用例断言它 — 补一条情景题并标 gates，` +
        `或判定它不值得占一个编号、降级成所在章节的散文`
    );
    failed++;
  }

  // 棘轮反向：已经补上用例的门禁必须从豁免表里删掉，否则豁免表会变成摆设。
  for (const [gate, why] of KNOWN_UNCOVERED_GATES) {
    if (!gates.includes(gate)) {
      report("fail", "fe-gate-coverage", `KNOWN_UNCOVERED 里的 ${gate} 已不存在，删掉这条`);
      failed++;
    } else if (covered.has(gate)) {
      report(
        "fail",
        "fe-gate-coverage",
        `${gate} 已有用例覆盖（${why}），把它从 KNOWN_UNCOVERED 删掉`
      );
      failed++;
    }
  }

  if (failed === 0) {
    report(
      "pass",
      "fe-gate-coverage",
      `${covered.size}/${gates.length} gates covered by evals, ` +
        `${KNOWN_UNCOVERED_GATES.size} known-uncovered`
    );
  }
}

// 注册表指向一份已删除的文件时，fe-link 抓不到（写成行内 code 而不是链接），
// 而 fe-id-prefix 现读这张表，等于把一个已下线的前缀继续算作已批准。
function checkFrontendRegistryTargets() {
  const content = readFileSync(ID_REGISTRY_PATH, "utf-8");
  const roots = [...FRONTEND_ROOTS, ROOT];
  let failed = 0;
  let count = 0;

  for (const match of content.matchAll(
    /`((?:references|agents|scripts|evals|tests)\/[^`*\s]+\.[a-z]{2,4})`/g
  )) {
    const target = match[1];
    count++;
    if (!roots.some((root) => existsSync(join(root, target)))) {
      report(
        "fail",
        "fe-registry-target",
        `${ID_REGISTRY} names "${target}" but no such file exists under the chain roots`
      );
      failed++;
    }
  }
  if (failed === 0) {
    report("pass", "fe-registry-target", `${count} registry file references all resolve`);
  }
}

function checkFrontendChain() {
  console.log("\n── 9. Frontend SDD Chain ──");

  const missing = FRONTEND_ROOTS.filter((dir) => !existsSync(dir));
  if (missing.length > 0) {
    for (const dir of missing) {
      report("fail", "fe-chain", `${rel(dir)} NOT FOUND`);
    }
    return;
  }

  const files = FRONTEND_ROOTS.flatMap(walkMarkdown);
  checkFrontendLinks(files);
  checkFrontendPathVariables(files);
  checkFrontendGateNumbers(files);
  checkFrontendDimensionNames(files);
  checkFrontendIdPrefixes(files);
  checkFrontendAgentStructure();
  checkFrontendScriptPaths(files);
  checkFrontendScriptOwners(files);
  checkFrontendRegistryTargets();
  checkFrontendGateCoverage();
}

// ── Run all checks ─────────────────────────────────────────────────

console.log("moon-skills Static Consistency Check");
console.log("====================================");

checkArtifactChain();
checkRouteTargets();
checkSingleOwnership();
checkWorkModeCoverage();
checkReferenceFiles();
checkImmuneGovernance();
checkUncertaintyProtocol();
checkPromptFiles();
checkFrontendChain();

console.log("\n====================================");
console.log(
  `Summary: ${totalPass} passed, ${totalFail} failed, ${totalWarn} warnings`
);
process.exit(totalFail > 0 ? 1 : 0);
