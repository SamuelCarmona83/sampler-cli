/**
 * Pi Extension: Sampler Integration
 *
 * This TypeScript extension adds high-level commands and tools
 * for working with sampler-cli directly inside Pi.
 *
 * Place it in ~/.pi/agent/extensions/sampler.ts
 * or load it temporarily with: pi -e ./sampler-pi-extension.ts
 */

import { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { StringEnum } from "@earendil-works/pi-ai";
import * as pathUtil from "path";

// ============================================
// Shared Helpers for Sampler Setup & Query
// ============================================

const ensuredProjects = new Set<string>();
const CONTEXT_CHAR_LIMIT = 3400;
const CACHE_TTL_MS = 5 * 60 * 1000;

const CONTEXT_CHAR_LIMIT_BY_ACTION: Record<string, number> = {
  search: 3400,
  overview: 3400,
  callers: 2400,
  usages: 2400,
  related: 2400,
  stale: 1800,
  list_projects: 1200,
};

const contextCache = new Map<string, { title: string; text: string; timestamp: number }>();

function formatForAgentContext(content: string, action: string = "search"): string {
  const limit = CONTEXT_CHAR_LIMIT_BY_ACTION[action] ?? CONTEXT_CHAR_LIMIT;
  const trimmed = (content || "").trim();
  if (!trimmed) return "(sin resultados)";
  if (trimmed.length <= limit) return trimmed;
  return `${trimmed.slice(0, limit).trim()}\n\n(... salida truncada; dime si necesitas más detalles.)`;
}

function cacheKeyForCommand(command: string): string {
  return command.trim();
}

function buildToolCacheKey(
  action: string,
  project?: string,
  query?: string,
  semantic?: boolean,
): string {
  return `tool:${action}:${project ?? "global"}:${query ?? ""}:${semantic ? "semantic" : "plain"}`;
}

function getCachedContext(key: string) {
  const entry = contextCache.get(key);
  if (!entry) return null;
  if (Date.now() - entry.timestamp > CACHE_TTL_MS) {
    contextCache.delete(key);
    return null;
  }
  return entry;
}

function storeCachedContext(key: string, title: string, text: string) {
  contextCache.set(key, { title, text, timestamp: Date.now() });
}

async function getCwdRoot(pi: ExtensionAPI): Promise<string> {
  const result = await pi.exec("bash", [
    "-c",
    "git rev-parse --show-toplevel 2>/dev/null || pwd",
  ]);
  return result.stdout.trim();
}

function getProjectNameFromPath(path: string): string {
  // Simple basename logic
  const parts = path.split(/[/\\]/);
  return parts[parts.length - 1] || "default";
}

async function ensureProjectReady(
  pi: ExtensionAPI,
  ctx: any,
  name: string,
  path: string,
  force: boolean = false,
): Promise<boolean> {
  if (ensuredProjects.has(name) && !force) return true;

  ctx.ui.notify(`Setting up sampler for project '${name}'...`, "info");

  // 1. Try to add project (ignore "already exists" error)
  const addResult = await pi.exec("bash", [
    "-c",
    `sampler project add "${name}" "${path}" --language auto`,
  ]);
  if (addResult.code !== 0 && !addResult.stderr.includes("already exists")) {
    ctx.ui.notify(`Failed to register project: ${addResult.stderr}`, "error");
    return false;
  }

  // 2. Index project (core graph: symbols, relationships, files)
  const indexCmd = force
    ? `sampler index "${name}" --plain --force`
    : `sampler index "${name}" --plain`;
  const indexResult = await pi.exec("bash", ["-c", indexCmd]);

  // Handle missing dependencies gracefully - core indexing still works
  if (indexResult.code !== 0) {
    const stderr = indexResult.stderr || indexResult.stdout;

    // Check for known optional dependency errors (BGE, numpy, etc.)
    if (
      stderr.includes("BGE") ||
      stderr.includes("numpy") ||
      stderr.includes("embeddings")
    ) {
      ctx.ui.notify(
        "Core indexing complete (semantic search requires optional deps: pip install 'sampler-cli[semantic,embeddings]').",
        "info",
      );
    } else {
      ctx.ui.notify(`Failed to index project: ${stderr}`, "error");
      return false;
    }
  } else {
    // Index succeeded - check if embeddings were generated
    if (
      indexResult.stdout.includes("Embedded") ||
      indexResult.stdout.includes("embed")
    ) {
      ctx.ui.notify("Project indexed with embeddings.", "success");
    } else {
      ctx.ui.notify(
        "Project indexed (semantic search unavailable without numpy).",
        "info",
      );
    }
  }

  ensuredProjects.add(name);
  ctx.ui.notify(`Project '${name}' is ready.`, "success");
  return true;
}

/**
 * Injects a block of text into the agent's context window as a custom message.
 * This makes sampler output visible for follow-up reasoning and manual references.
 *
 * Note: `ctx.agent.submitMessage` does not exist in Pi's ExtensionContext API.
 * The real API is `pi.sendMessage()` on the ExtensionAPI object.
 */
async function injectAgentContext(
  pi: ExtensionAPI,
  ctx: any,
  title: string,
  content: string,
) {
  const formatted = formatForAgentContext(content);
  pi.sendMessage({
    customType: "sampler",
    content: `### Sampler Result: ${title}\n\n${formatted}`,
    display: true,
  });
  return formatted;
}

/**
 * Cleans sampler output to be more agent-friendly.
 * Strips "projectName:" prefix from lines to prevent path duplication issues in agent reasoning.
 */
function cleanSamplerOutput(output: string, projectName: string): string {
  if (!output || !projectName) return output || "";
  const escaped = projectName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  // Match project name at start of line, optionally after tree-drawing chars/spaces
  const regex = new RegExp(`^(\\s*[│├└─▎]?\\s*)${escaped}:`, "gm");
  return output.replace(regex, "$1");
}

/**
 * Shared helper to run a sampler command, display it nicely, and inject the
 * result into the agent's context window so it can reason about it.
 */
async function runAndReport(
  pi: ExtensionAPI,
  ctx: any,
  title: string,
  cmd: string,
  projectName?: string,
  successType: "success" | "info" = "success",
) {
  const cacheKey = cacheKeyForCommand(cmd);
  const cached = getCachedContext(cacheKey);
  if (cached) {
    ctx.ui.notify(
      `▶ ${cmd}\n✓ Reutilizando resultado en caché`,
      successType,
    );
    await injectAgentContext(pi, ctx, cached.title, cached.text);
    return { code: 0, stdout: cached.text, stderr: "" };
  }

  const result = await pi.exec("bash", ["-c", cmd]);
  const isSuccess = result.code === 0;
  const rawOutput = (result.stdout || result.stderr || "").trim();

  const output = isSuccess && projectName
    ? cleanSamplerOutput(rawOutput, projectName)
    : rawOutput;

  if (isSuccess && output) {
    const finalTitle = `${title}\nUser manually executed \`${cmd}\``;
    const injected = await injectAgentContext(pi, ctx, finalTitle, output);
    storeCachedContext(cacheKey, finalTitle, injected);
  }

  ctx.ui.notify(
    `▶ ${cmd}\n${isSuccess ? "✓ Results added to context" : output || "(no output)"}`,
    isSuccess ? successType : "error",
  );

  return {
    ...result,
    stdout: output,
    stderr: isSuccess ? "" : result.stderr,
  };
}

/**
 * Resolves which project to use. If explicitProject is provided, we assume it's already registered.
 * Otherwise, we auto-detect from CWD and ensure it's indexed.
 */
async function resolveProject(
  pi: ExtensionAPI,
  ctx: any,
  explicitProject?: string,
): Promise<{ name: string; path: string } | null> {
  if (explicitProject) {
    return { name: explicitProject, path: "" }; // Path not needed for registered projects
  }

  const root = await getCwdRoot(pi);
  const name = getProjectNameFromPath(root);
  const success = await ensureProjectReady(pi, ctx, name, root);
  return success ? { name, path: root } : null;
}

export default function (pi: ExtensionAPI) {
  // ============================================
  // 1. Register useful commands
  // ============================================

  pi.registerCommand("sampler:search", {
    description: "Semantic or structural search in the codebase using sampler",
    handler: async (args, ctx) => {
      const argsArray = Array.isArray(args)
        ? args
        : args
          ? args.split(/\s+/)
          : [];
      const query =
        argsArray.find((a) => !a.startsWith("-")) ||
        (await ctx.ui.input("Search query:"));
      if (!query) return;

      const useSemantic =
        argsArray.includes("--semantic") ||
        (await ctx.ui.confirm("Use semantic search?", "Semantic search uses embeddings and may require additional dependencies."));

      const explicitProjectIdx = argsArray.indexOf("--project");
      const explicitProject =
        explicitProjectIdx !== -1
          ? argsArray[explicitProjectIdx + 1]
          : undefined;

      const resolved = await resolveProject(pi, ctx, explicitProject);
      if (!resolved) return;

      const runSearch = async () => {
        const cmd = useSemantic
          ? `sampler search "${query}" --semantic --project "${resolved.name}" --limit 15 --style bars`
          : `sampler search "${query}" --project "${resolved.name}" --limit 15 --style bars`;
        return runAndReport(pi, ctx, `Search: ${query}`, cmd, resolved.name);
      };

      let result = await runSearch();

      // Fallback: If semantic search fails (possibly missing embeddings), try to embed and retry once
      if (useSemantic && result.code !== 0) {
        const stderr = result.stderr || result.stdout;
        if (
          stderr.includes("numpy") ||
          stderr.includes("semantic") ||
          stderr.includes("embeddings")
        ) {
          ctx.ui.notify(
            "Missing deps (pip install 'sampler-cli[semantic,embeddings]'). Falling back to keyword search.",
            "warning",
          );
          // Fallback to non-semantic search
          const fallbackCmd = `sampler search "${query}" --project "${resolved.name}" --limit 15`;
          result = await runAndReport(
            pi,
            ctx,
            `Search (fallback): ${query}`,
            fallbackCmd,
            resolved.name,
          );
        } else if (
          stderr.includes("requires embeddings") ||
          stderr.includes("not found")
        ) {
          ctx.ui.notify("Generating embeddings for semantic search...", "info");
          await pi.exec("bash", ["-c", `sampler embed "${resolved.name}"`]);
          result = await runSearch();
        }
      }
    },
  });

  pi.registerCommand("sampler:callers", {
    description: "Find who calls a symbol using sampler",
    handler: async (args, ctx) => {
      const argsArray = Array.isArray(args)
        ? args
        : args
          ? args.split(/\s+/)
          : [];
      let symbol = argsArray.find((a) => !a.startsWith("-"));
      if (!symbol) {
        symbol = await ctx.ui.input("Symbol name (or path:symbol):");
      }
      if (!symbol) return;

      const explicitProjectIdx = argsArray.indexOf("--project");
      const explicitProject =
        explicitProjectIdx !== -1
          ? argsArray[explicitProjectIdx + 1]
          : undefined;
      const resolved = await resolveProject(pi, ctx, explicitProject);
      if (!resolved) return;

      await runAndReport(
        pi,
        ctx,
        `Callers of ${symbol}`,
        `sampler callers "${symbol}" --project "${resolved.name}" --style bars`,
        resolved.name,
      );
    },
  });

  pi.registerCommand("sampler:usages", {
    description: "Find usages of a symbol",
    handler: async (args, ctx) => {
      const argsArray = Array.isArray(args)
        ? args
        : args
          ? args.split(/\s+/)
          : [];
      let symbol = argsArray.find((a) => !a.startsWith("-"));
      if (!symbol) symbol = await ctx.ui.input("Symbol name:");
      if (!symbol) return;

      const explicitProjectIdx = argsArray.indexOf("--project");
      const explicitProject =
        explicitProjectIdx !== -1
          ? argsArray[explicitProjectIdx + 1]
          : undefined;
      const resolved = await resolveProject(pi, ctx, explicitProject);
      if (!resolved) return;

      await runAndReport(
        pi,
        ctx,
        `Usages of ${symbol}`,
        `sampler usages "${symbol}" --project "${resolved.name}" --style bars`,
        resolved.name,
      );
    },
  });

  pi.registerCommand("sampler:related", {
    description: "Find related symbols in the graph",
    handler: async (args, ctx) => {
      const argsArray = Array.isArray(args)
        ? args
        : args
          ? args.split(/\s+/)
          : [];
      let symbol = argsArray.find((a) => !a.startsWith("-"));
      if (!symbol) symbol = await ctx.ui.input("Symbol name:");
      if (!symbol) return;

      const explicitProjectIdx = argsArray.indexOf("--project");
      const explicitProject =
        explicitProjectIdx !== -1
          ? argsArray[explicitProjectIdx + 1]
          : undefined;
      const resolved = await resolveProject(pi, ctx, explicitProject);
      if (!resolved) return;

      await runAndReport(
        pi,
        ctx,
        `Related to ${symbol}`,
        `sampler related "${symbol}" --project "${resolved.name}" --style bars`,
        resolved.name,
      );
    },
  });

  pi.registerCommand("sampler:overview", {
    description: "Get structural overview of a file",
    handler: async (args, ctx) => {
      const argsArray = Array.isArray(args)
        ? args
        : args
          ? args.split(/\s+/)
          : [];
      let file = argsArray.find((a) => !a.startsWith("-"));
      if (!file) file = await ctx.ui.input("File path:");
      if (!file) return;

      // side effect: ensure project for current dir is indexed so overview works better
      const resolved = await resolveProject(pi, ctx);
      const baseDir = resolved?.path || process.cwd();
      const absoluteFile = pathUtil.isAbsolute(file) ? file : pathUtil.resolve(baseDir, file);

      await runAndReport(
        pi,
        ctx,
        `Overview of ${absoluteFile}`,
        `sampler overview "${absoluteFile}" --style bars`,
        resolved?.name,
      );
    },
  });

  pi.registerCommand("sampler:stale", {
    description: "Find potentially stale code (only called from tests)",
    handler: async (args, ctx) => {
      const argsArray = Array.isArray(args)
        ? args
        : args
          ? args.split(/\s+/)
          : [];
      const explicitProject = argsArray.find((a) => !a.startsWith("-"));
      const resolved = await resolveProject(pi, ctx, explicitProject);
      if (!resolved) return;

      await runAndReport(
        pi,
        ctx,
        `Stale code in ${resolved.name}`,
        `sampler stale-code "${resolved.name}" --limit 15`,
        resolved.name,
      );
    },
  });

  pi.registerCommand("sampler:projects", {
    description: "List all registered projects",
    handler: async (args, ctx) => {
      await runAndReport(
        pi,
        ctx,
        "Registered Projects",
        "sampler project list",
        undefined,
        "info",
      );
    },
  });

  // Alias command to ensure /sampler:project also adds to context
  pi.registerCommand("sampler:project", {
    description: "Alias for listing registered projects",
    handler: async (args, ctx) => {
      await runAndReport(
        pi,
        ctx,
        "Registered Projects",
        "sampler project list",
        undefined,
        "info",
      );
    },
  });

  pi.registerCommand("sampler:remove", {
    description: "Remove a registered project",
    handler: async (args, ctx) => {
      const argsArray = Array.isArray(args)
        ? args
        : args
          ? args.split(/\s+/)
          : [];
      let name = argsArray[0];
      if (!name) name = await ctx.ui.input("Project name to remove:");
      if (!name) return;

      const result = await pi.exec("bash", [
        "-c",
        `sampler project remove "${name}"`,
      ]);
      if (result.code === 0) {
        ensuredProjects.delete(name);
        ctx.ui.notify(`Project '${name}' removed.`, "info");
      } else {
        ctx.ui.notify(result.stderr || result.stdout, "error");
      }
    },
  });

  // ============================================
  // 2. Register a high-level tool that the LLM
  // can call directly. Tool results are returned
  // to the agent automatically; slash-command
  // results are also injected into context via
  // injectAgentContext so the user can refer to
  // them manually.
  // ============================================

  const nextStepTemplates: Record<string, string> = {
    search: 'Sugerido: action=callers o related sobre "{query}".',
    callers: 'Sugerido: action=related o usages sobre "{query}".',
    usages: 'Sugerido: action=overview o related sobre "{query}".',
    related: 'Sugerido: action=callers o search sobre "{query}".',
    overview: 'Sugerido: action=callers/related sobre símbolo destacado.',
    stale: 'Sugerido: action=callers/overview para verificar en "{project}".',
  };

  function formatAndCache(cacheKey: string, title: string, raw: string): string {
    const formatted = formatForAgentContext(raw);
    storeCachedContext(cacheKey, title, formatted);
    return formatted;
  }

  function renderNextStep(action: string, query?: string, project?: string): string {
    const template = nextStepTemplates[action];
    if (!template) return "";
    return template
      .replace(/\{query\}/g, query || "esta consulta")
      .replace(/\{project\}/g, project || "este proyecto");
  }

  pi.registerTool({
    name: "sampler_explore_codebase",
    label: "Explore Codebase",
    description:
      "Explore an indexed codebase using sampler: structural/semantic search, callers, usages, related symbols, file overview, and stale-code detection. " +
      "Use this instead of grep/find when asking architectural questions ('who calls X', 'what's related to Y', 'is Z used anywhere'). " +
      "Always inspect the returned 'nextSteps' hint and consider calling this tool again with a follow-up action before answering the user.",
    promptSnippet:
      "Explore indexed codebase structure: search, callers, usages, related, overview, stale, list_projects",
    promptGuidelines: [
      "Use sampler_explore_codebase before making architectural claims about the current project (callers, usages, related symbols).",
      "Use sampler_explore_codebase with action=list_projects to check which projects are already indexed before assuming none exist.",
      "Chain sampler_explore_codebase calls: after a search or callers result, call it again with action=related or action=callers on an interesting symbol instead of stopping.",
      "Manual slash commands like /sampler:search results are also visible in your context window for follow-up questions.",
    ],
    parameters: Type.Object({
      action: StringEnum(
        [
          "search",
          "callers",
          "usages",
          "related",
          "overview",
          "stale",
          "list_projects",
        ] as const,
        {
          description: "What to do",
        },
      ),
      query: Type.Optional(
        Type.String({
          description:
            "Symbol name, file path, or search query (omit for list_projects)",
        }),
      ),
      semantic: Type.Optional(
        Type.Boolean({
          description: "Use semantic search (only for action=search)",
        }),
      ),
      project: Type.Optional(
        Type.String({ description: "Optional project name override" }),
      ),
      force: Type.Optional(
        Type.Boolean({ description: "Force re-index project before querying" }),
      ),
    }),
    async execute(toolCallId, params, signal, onUpdate, ctx) {
      const {
        action,
        query,
        semantic = false,
        project: explicitProject,
        force = false,
      } = params;

      const actionSafe = action as string;

      if (actionSafe === "list_projects") {
        const cacheKey = buildToolCacheKey("list_projects");
        const cached = getCachedContext(cacheKey);
        if (cached) {
          ctx.ui.notify(
            "▶ sampler project list\n✓ Reutilizando lista de proyectos registrada",
            "info",
          );
          return {
            content: [{ type: "text", text: cached.text }],
            details: { action: actionSafe, success: true },
          };
        }

        const cmd = "sampler project list";
        const result = await pi.exec("bash", ["-c", cmd], {
          signal,
        });
        const text =
          result.stdout || result.stderr || "(no projects registered)";
        // Normalize display: strip potential "(branch)" suffixes from each line for readability
        const cleanText = text
          .split("\n")
          .map((line) => line.replace(/\s*\([^)]*\)\s*$/, ""))
          .join("\n");

        //const formatted = await injectAgentContext(pi, ctx, "Registered Projects", cleanText);
        const formatted = formatForAgentContext(cleanText);
        if (result.code === 0) {
          storeCachedContext(cacheKey, "Registered Projects", formatted);
        }
        ctx.ui.notify(
          `▶ ${cmd}\n${result.code === 0 ? "✓ Results added to context" : cleanText}`,
          result.code === 0 ? "info" : "error",
        );
        return {
          content: [{ type: "text", text: result.code === 0 ? formatted : cleanText }],
          details: { action: actionSafe, success: result.code === 0 },
        };
      }

      if (!query && actionSafe !== "list_projects" && actionSafe !== "stale") {
        throw new Error(
          `action=${action} requires 'query'. ` +
          (actionSafe === "overview"
            ? "Pass a file path (relative to project root or absolute), not a project name."
            : "Pass a symbol name.")
        );
      }
      const resolved = await resolveProject(pi, ctx, explicitProject);
      if (!resolved) {
        throw new Error("Could not resolve or index the current project");
      }

      if (force) {
        await ensureProjectReady(pi, ctx, resolved.name, resolved.path, true);
      }

      const cacheKey = buildToolCacheKey(
        actionSafe,
        resolved.name,
        query,
        semantic,
      );
      if (!force) {
        const cached = getCachedContext(cacheKey);
        if (cached) {
          ctx.ui.notify(
            `▶ sampler_explore_codebase (${actionSafe})\n✓ Reutilizando resultado previo`,
            "info",
          );
          formatAndCache(cacheKey, cached.title, cached.text);
          return {
            content: [{ type: "text", text: cached.text }],
            details: { action: actionSafe, project: resolved.name, success: true },
          };
        }
      }

      const runCmd = async (c: string) => {
        let res = await pi.exec("bash", ["-c", c], { signal });
        // Handle CLI version mismatch: some versions might not support --style yet
        if (
          res.code !== 0 &&
          (res.stderr.includes("No such option '--style'") ||
            res.stdout.includes("No such option '--style'"))
        ) {
          const fallback = c.replace(/\s+--style\s+\S+/, "");
          res = await pi.exec("bash", ["-c", fallback], { signal });
        }
        return res;
      };

      let cmd = "";
      switch (actionSafe) {
        case "search":
          cmd = semantic
            ? `sampler search "${query}" --semantic --project "${resolved.name}" --limit 12 --style bars`
            : `sampler search "${query}" --project "${resolved.name}" --limit 12 --style bars`;
          break;
        case "callers":
          cmd = `sampler callers "${query}" --project "${resolved.name}" --style bars`;
          break;
        case "usages":
          cmd = `sampler usages "${query}" --project "${resolved.name}" --style bars`;
          break;
        case "related":
          cmd = `sampler related "${query}" --project "${resolved.name}" --style bars`;
          break;

        case "overview":
          const baseDir = resolved.path || (await getCwdRoot(pi));
          const absoluteFile = pathUtil.isAbsolute(query!)
            ? query!
            : pathUtil.resolve(baseDir, query!);
          cmd = `sampler overview "${absoluteFile}" --style bars`;
          break;

        case "stale":
          cmd = `sampler stale-code "${resolved.name}" --limit 15`;
          break;
      }

      let result = await runCmd(cmd);

      // Fallback for semantic search missing deps
      let note = "";
      if (actionSafe === "search" && semantic && result.code !== 0) {
        const stderr = result.stderr || result.stdout;
        if (
          stderr.includes("numpy") ||
          stderr.includes("semantic") ||
          stderr.includes("embeddings")
        ) {
          const fallbackCmd = `sampler search "${query}" --project "${resolved.name}" --limit 12`;
          result = await runCmd(fallbackCmd);
          note =
            "(Semantic search unavailable [missing deps: pip install 'sampler-cli[semantic,embeddings]'], showing keyword results instead)\n\n";
        } else if (
          stderr.includes("requires embeddings") ||
          stderr.includes("not found")
        ) {
          await pi.exec("bash", ["-c", `sampler embed "${resolved.name}"`], {
            signal,
          });
          result = await runCmd(cmd);
        }
      }

      if (result.code !== 0) {
        throw new Error(
          result.stderr || result.stdout || `sampler ${actionSafe} failed`,
        );
      }

      const title = `Sampler ${actionSafe}${query ? `: ${query}` : ""}`;
      const output = cleanSamplerOutput(
        result.stdout || result.stderr || "",
        resolved.name,
      );
      const nextStep = renderNextStep(actionSafe, query, resolved.name);
      const textParts: string[] = [];
      if (note) textParts.push(note.trim());
      if (output) textParts.push(output.trim());
      if (nextStep) textParts.push(nextStep);
      const text = textParts.join("\n\n");

      const formattedText = await injectAgentContext(pi, ctx, title, text);
      storeCachedContext(cacheKey, title, formattedText);
      ctx.ui.notify(
        `▶ ${cmd}\n✓ Results added to context`,
        "info",
      );

      return {
        content: [{ type: "text", text: formattedText }],
        details: { action: actionSafe, project: resolved.name, success: true },
      };
    },
  });

  // ============================================
  // 3. Nudge the agent toward sampler before edits
  // ============================================

  pi.on("tool_call", async (event, ctx) => {
    if (event.toolName === "edit" || event.toolName === "write") {
      const file = (event.input as { path?: string })?.path;
      if (file) {
        ctx.ui.notify(
          `Tip: Consider calling sampler_explore_codebase (action=callers/related) on key symbols in ${file} first.`,
          "info",
        );
      }
    }
  });

  pi.on("before_agent_start", async (event, ctx) => {
    return {
      message: {
        customType: "sampler",
        content:
          "You have access to the sampler_explore_codebase tool for codebase exploration.",
        display: false,
      },
    };
  });
}
