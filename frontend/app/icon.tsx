/**
 * Favicon - 주식 분석 앱 아이콘
 * 📊 차트 아이콘
 */

import { ImageResponse } from "next/og";

export const size = {
  width: 32,
  height: 32,
};

export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          fontSize: 24,
          background: "linear-gradient(to bottom right, #3b82f6, #1d4ed8)",
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          borderRadius: "4px",
        }}
      >
        📊
      </div>
    ),
    {
      ...size,
    }
  );
}
