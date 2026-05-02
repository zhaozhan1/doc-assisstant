import { Segmented } from "antd";
import { useWritingStore } from "../../stores/useWritingStore";
import { OneStepMode } from "./OneStepMode";
import { StepByStepMode } from "./StepByStepMode";
import { WordToPptMode } from "./WordToPptMode";
import type { WritingMode } from "../../stores/useWritingStore";

const modeOptions: { label: string; value: WritingMode }[] = [
  { label: "一步生成", value: "onestep" },
  { label: "分步检索", value: "stepbystep" },
  { label: "Word→PPT", value: "wordtoppt" },
];

export function Writing() {
  const mode = useWritingStore((s) => s.mode);
  const setMode = useWritingStore((s) => s.setMode);

  const renderMode = () => {
    switch (mode) {
      case "onestep":
        return <OneStepMode />;
      case "stepbystep":
        return <StepByStepMode />;
      case "wordtoppt":
        return <WordToPptMode />;
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div
        style={{
          padding: "16px 24px",
          borderBottom: "1px solid #f0f0f0",
          display: "flex",
          justifyContent: "center",
        }}
      >
        <Segmented
          options={modeOptions}
          value={mode}
          onChange={(val) => setMode(val as WritingMode)}
        />
      </div>
      <div style={{ flex: 1, padding: 16, overflow: "hidden" }}>
        {renderMode()}
      </div>
    </div>
  );
}

export default Writing;
