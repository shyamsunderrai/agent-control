import {
  Box,
  Group,
  ScrollArea,
  SegmentedControl,
  Stack,
  Textarea,
} from "@mantine/core";

import { JsonEditor } from "@/components/json-editor";

import type { EvaluatorJsonViewProps, JsonViewMode } from "./types";

const JSON_VIEW_HEIGHT = 400;

export const EvaluatorJsonView = ({
  config,
  onChange,
  jsonViewMode,
  onJsonViewModeChange,
  rawJsonText,
  onRawJsonTextChange,
  rawJsonError,
}: EvaluatorJsonViewProps) => {
  const handleModeChange = (value: string) => {
    onJsonViewModeChange(value as JsonViewMode);
  };

  return (
    <Stack gap='sm'>
      {/* Tree/Raw sub-toggle */}
      <Group justify='flex-end'>
        <SegmentedControl
          value={jsonViewMode}
          onChange={handleModeChange}
          data={[
            { value: "tree", label: "Tree" },
            { value: "raw", label: "Raw" },
          ]}
          size='xs'
        />
      </Group>

      {jsonViewMode === "tree" ? (
        <ScrollArea h={JSON_VIEW_HEIGHT} type='auto'>
          <Box p='xs'>
            <JsonEditor
              data={config}
              setData={onChange}
              rootName='config'
              restrictEdit={false}
              restrictDelete={false}
              restrictAdd={false}
              collapse={false}
              rootFontSize={12}
            />
          </Box>
        </ScrollArea>
      ) : (
        <Textarea
          value={rawJsonText}
          onChange={(e) => onRawJsonTextChange(e.currentTarget.value)}
          rows={18}
          styles={{
            input: {
              fontFamily: "monospace",
              fontSize: 12,
              height: JSON_VIEW_HEIGHT,
              overflow: "auto",
            },
          }}
          error={rawJsonError}
          data-testid='raw-json-textarea'
        />
      )}
    </Stack>
  );
};
