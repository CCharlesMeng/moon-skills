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

// ── Run all checks ─────────────────────────────────────────────────

console.log("moon-skills Static Consistency Check");
console.log("====================================");

checkArtifactChain();
checkRouteTargets();
checkSingleOwnership();
checkWorkModeCoverage();
checkReferenceFiles();

console.log("\n====================================");
console.log(
  `Summary: ${totalPass} passed, ${totalFail} failed, ${totalWarn} warnings`
);
process.exit(totalFail > 0 ? 1 : 0);
