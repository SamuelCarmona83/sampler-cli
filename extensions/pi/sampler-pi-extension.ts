/**
 * Pi Extension: Sampler Integration
 * 
 * This TypeScript extension adds high-level commands and tools
 * for working with sampler-cli directly inside Pi.
 * 
 * Place it in ~/.pi/agent/extensions/sampler.ts
 * or load it temporarily with: pi -e ./sampler-pi-extension.ts
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  // ============================================
  // 1. Register useful commands
  // ============================================

  pi.registerCommand("sampler:search", {
    description: "Semantic or structural search in the codebase using sampler",
    handler: async (args, ctx) => {
      const query = args[0] || await ctx.ui.input("Search query:");
      if (!query) return;

      const useSemantic = args.includes("--semantic") || 
                          await ctx.ui.confirm("Use semantic search?", false);

      const cmd = useSemantic 
        ? `sampler search "${query}" --semantic --limit 15`
        : `sampler search "${query}" --limit 15`;

      const result = await ctx.bash(cmd);
      ctx.ui.notify(result.stdout || result.stderr, result.code === 0 ? "success" : "error");
    },
  });

  pi.registerCommand("sampler:callers", {
    description: "Find who calls a symbol using sampler",
    handler: async (args, ctx) => {
      let symbol = args[0];
      if (!symbol) {
        symbol = await ctx.ui.input("Symbol name (or path:symbol):");
      }
      if (!symbol) return;

      const result = await ctx.bash(`sampler callers "${symbol}" --style bars`);
      ctx.ui.notify(result.stdout || result.stderr, result.code === 0 ? "success" : "error");
    },
  });

  pi.registerCommand("sampler:usages", {
    description: "Find usages of a symbol",
    handler: async (args, ctx) => {
      let symbol = args[0];
      if (!symbol) symbol = await ctx.ui.input("Symbol name:");
      if (!symbol) return;

      const result = await ctx.bash(`sampler usages "${symbol}" --style bars`);
      ctx.ui.notify(result.stdout || result.stderr, result.code === 0 ? "success" : "error");
    },
  });

  pi.registerCommand("sampler:related", {
    description: "Find related symbols in the graph",
    handler: async (args, ctx) => {
      let symbol = args[0];
      if (!symbol) symbol = await ctx.ui.input("Symbol name:");
      if (!symbol) return;

      const result = await ctx.bash(`sampler related "${symbol}" --style bars`);
      ctx.ui.notify(result.stdout || result.stderr, result.code === 0 ? "success" : "error");
    },
  });

  pi.registerCommand("sampler:overview", {
    description: "Get structural overview of a file",
    handler: async (args, ctx) => {
      let file = args[0];
      if (!file) file = await ctx.ui.input("File path:");
      if (!file) return;

      const result = await ctx.bash(`sampler overview "${file}" --style bars`);
      ctx.ui.notify(result.stdout || result.stderr, result.code === 0 ? "success" : "error");
    },
  });

  pi.registerCommand("sampler:stale", {
    description: "Find potentially stale code (only called from tests)",
    handler: async (args, ctx) => {
      const project = args[0] || "current";
      const result = await ctx.bash(`sampler stale-code ${project} --limit 20`);
      ctx.ui.notify(result.stdout || result.stderr, result.code === 0 ? "success" : "error");
    },
  });

  // ============================================
  // 2. (Optional) Register a high-level tool
  //    that the LLM can call directly
  // ============================================

  pi.registerTool({
    name: "sampler_explore_codebase",
    description: "Explore the codebase using sampler. Use this for architectural questions, finding callers/usages, or semantic search.",
    parameters: {
      type: "object",
      properties: {
        action: {
          type: "string",
          enum: ["search", "callers", "usages", "related", "overview", "stale"],
          description: "What to do"
        },
        query: {
          type: "string",
          description: "Symbol name, file path, or search query"
        },
        semantic: {
          type: "boolean",
          description: "Use semantic search (only for action=search)"
        }
      },
      required: ["action", "query"]
    },
    handler: async ({ action, query, semantic = false }, ctx) => {
      let cmd = "";

      switch (action) {
        case "search":
          cmd = semantic 
            ? `sampler search "${query}" --semantic --limit 12`
            : `sampler search "${query}" --limit 12`;
          break;
        case "callers":
          cmd = `sampler callers "${query}" --style bars`;
          break;
        case "usages":
          cmd = `sampler usages "${query}" --style bars`;
          break;
        case "related":
          cmd = `sampler related "${query}" --style bars`;
          break;
        case "overview":
          cmd = `sampler overview "${query}" --style bars`;
          break;
        case "stale":
          cmd = `sampler stale-code current --limit 15`;
          break;
      }

      if (!cmd) return { error: "Unknown action" };

      const result = await ctx.bash(cmd);
      return {
        output: result.stdout || result.stderr,
        success: result.code === 0
      };
    }
  });

  // ============================================
  // 3. Optional: Auto-suggest using sampler on certain events
  // ============================================

  pi.on("beforeToolCall", async (toolName, args, ctx) => {
    // Example: if the agent is about to edit a file, suggest checking callers first
    if (toolName === "edit" || toolName === "write") {
      const file = args[0];
      if (file && typeof file === "string") {
        ctx.ui.notify(
          `Tip: Consider running 'sampler callers' or 'sampler related' on key symbols in ${file} first.`,
          "info"
        );
      }
    }
  });

  console.log("[sampler] Pi extension loaded successfully");
}
