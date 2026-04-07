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

console.log("\n====================================");
console.log(
  `Summary: ${totalPass} passed, ${totalFail} failed, ${totalWarn} warnings`
);
process.exit(totalFail > 0 ? 1 : 0);
