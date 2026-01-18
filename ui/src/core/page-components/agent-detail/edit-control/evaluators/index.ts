/**
 * Evaluator Plugin Registry
 *
 * This module exports all available evaluator plugins and provides
 * utilities for working with them.
 *
 * ## Adding a New Evaluator Plugin
 *
 * 1. Create a new folder under `evaluators/` (e.g., `evaluators/my-plugin/`)
 * 2. Create the following files:
 *    - `types.ts` - Form value types
 *    - `form.tsx` - React form component
 *    - `index.ts` - Plugin definition (implements EvaluatorPlugin interface)
 * 3. Import and add the plugin to the `plugins` array below
 * 4. That's it! The main edit-control component will automatically pick it up.
 *
 * @example
 * ```typescript
 * // evaluators/my-plugin/index.ts
 * import type { EvaluatorPlugin } from "../types";
 * import { MyForm } from "./form";
 * import type { MyFormValues } from "./types";
 *
 * export const myPlugin: EvaluatorPlugin<MyFormValues> = {
 *   id: "my-plugin",
 *   displayName: "My Plugin",
 *   initialValues: { ... },
 *   validate: { ... },
 *   toConfig: (values) => ({ ... }),
 *   fromConfig: (config) => ({ ... }),
 *   FormComponent: MyForm,
 * };
 * ```
 */

import { jsonPlugin } from "./json";
import { listPlugin } from "./list";
import { luna2Plugin } from "./luna2";
import { regexPlugin } from "./regex";
import { sqlPlugin } from "./sql";
import type { AnyEvaluatorPlugin } from "./types";

/**
 * All registered evaluator plugins.
 * Add new plugins here to make them available in the UI.
 */
export const plugins: AnyEvaluatorPlugin[] = [
  regexPlugin,
  listPlugin,
  jsonPlugin,
  sqlPlugin,
  luna2Plugin,
];

/**
 * Map of plugin ID to plugin for quick lookup.
 */
export const pluginRegistry = new Map<string, AnyEvaluatorPlugin>(
  plugins.map((p) => [p.id, p])
);

/**
 * Get a plugin by ID.
 * Returns undefined if the plugin is not found.
 */
export const getPlugin = (id: string): AnyEvaluatorPlugin | undefined =>
  pluginRegistry.get(id);

/**
 * Check if a plugin exists.
 */
export const hasPlugin = (id: string): boolean => pluginRegistry.has(id);

// Re-export types and individual plugins for direct imports
export { jsonPlugin } from "./json";
export { listPlugin } from "./list";
export { luna2Plugin } from "./luna2";
export { regexPlugin } from "./regex";
export { sqlPlugin } from "./sql";
export type {
  AnyEvaluatorPlugin,
  EvaluatorFormProps,
  EvaluatorPlugin,
} from "./types";
