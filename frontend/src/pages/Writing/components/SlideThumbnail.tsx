import React from "react";
import type { SlideContent } from "../../../types/api";

interface Props {
  slide: SlideContent;
  index: number;
  total: number;
}

const TYPE_STYLES: Record<string, { bg: string; color: string }> = {
  cover: { bg: "linear-gradient(135deg, #1a3a5c, #2c5282)", color: "#fff" },
  toc: { bg: "linear-gradient(135deg, #f7f8fa, #edf0f5)", color: "#595959" },
  chapter: { bg: "#fff", color: "#595959" },
  conclusion: {
    bg: "linear-gradient(135deg, #1a3a5c, #2c5282)",
    color: "#fff",
  },
};

const SlideThumbnail: React.FC<Props> = ({ slide, index, total }) => {
  const style = TYPE_STYLES[slide.slide_type] || TYPE_STYLES.chapter;

  return (
    <div
      style={{
        aspectRatio: "16/10",
        borderRadius: 6,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        background: style.bg,
        color: style.color,
        border:
          slide.slide_type === "chapter" ? "1px solid #e8e8e8" : undefined,
        padding: 8,
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div style={{ fontWeight: 500, fontSize: 12, marginBottom: 4 }}>
        {slide.title}
      </div>
      {slide.bullets.length > 0 && (
        <div
          style={{
            fontSize: 9,
            opacity: 0.7,
            lineHeight: 1.4,
            textAlign: "center",
          }}
        >
          {slide.bullets.slice(0, 4).map((b, i) => (
            <div key={i}>&bull; {b}</div>
          ))}
        </div>
      )}
      <span
        style={{
          position: "absolute",
          bottom: 4,
          right: 6,
          fontSize: 9,
          opacity: 0.7,
        }}
      >
        {index + 1}/{total}
      </span>
    </div>
  );
};

export default SlideThumbnail;
