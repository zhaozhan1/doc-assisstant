import React from "react";

interface Props {
  currentStep: number; // 0-based, 0=pending, 1=parsing, 2=summarizing, 3=generating
  totalSteps: number;
  error: string | null;
}

const STEP_LABELS = ["文档解析", "内容分析", "AI 摘要", "生成文件"];

const GenerationSteps: React.FC<Props> = ({
  currentStep,
  totalSteps,
  error,
}) => {
  return (
    <div style={{ width: "100%", maxWidth: 320 }}>
      {STEP_LABELS.slice(0, totalSteps).map((label, i) => {
        let dotStyle: React.CSSProperties = {
          width: 20,
          height: 20,
          borderRadius: "50%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 10,
          flexShrink: 0,
          border: "1.5px solid #d9d9d9",
          color: "#bfbfbf",
        };
        let labelStyle: React.CSSProperties = {
          fontSize: 13,
          color: "#bfbfbf",
        };

        if (i < currentStep) {
          dotStyle = {
            ...dotStyle,
            background: "#f6ffed",
            color: "#52c41a",
            borderColor: "#b7eb8f",
          };
          labelStyle = {
            ...labelStyle,
            color: "#52c41a",
            textDecoration: "line-through",
            opacity: 0.7,
          };
        } else if (i === currentStep && !error) {
          dotStyle = {
            ...dotStyle,
            background: "#e6f7ff",
            color: "#1677ff",
            borderColor: "#91caff",
          };
          labelStyle = { ...labelStyle, color: "#1677ff", fontWeight: 500 };
        } else if (i === currentStep && error) {
          dotStyle = {
            ...dotStyle,
            background: "#fff2f0",
            color: "#ff4d4f",
            borderColor: "#ffccc7",
          };
          labelStyle = { ...labelStyle, color: "#ff4d4f", fontWeight: 500 };
        }

        return (
          <div
            key={i}
            style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}
          >
            <div style={dotStyle}>
              {i < currentStep
                ? "\u2713"
                : i === currentStep && error
                  ? "\u2715"
                  : i + 1}
            </div>
            <span style={labelStyle}>{label}</span>
            {i === currentStep && error && (
              <span
                style={{ fontSize: 11, color: "#ff7875", marginLeft: "auto" }}
              >
                失败
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default GenerationSteps;
