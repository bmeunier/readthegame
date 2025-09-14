import React from 'react';

export type Segment = {
  start_seconds: number;
  end_seconds: number;
  speaker_global_id: string | null;
  text: string;
  confidence?: number | null;
};

export default function Transcript({ segments }: { segments: Segment[] }) {
  return (
    <div style={{ lineHeight: 1.6 }}>
      {segments.map((s, idx) => (
        <div key={idx} style={{ marginBottom: 8 }}>
          <code style={{ opacity: 0.7 }}>
            [{formatTime(s.start_seconds)}–{formatTime(s.end_seconds)}]
          </code>{' '}
          <strong>{s.speaker_global_id ?? 'Unknown'}</strong>: {s.text}
        </div>
      ))}
    </div>
  );
}

function formatTime(sec: number) {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}