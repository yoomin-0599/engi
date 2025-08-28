// frontend/news-app/src/components/KeywordNetwork.tsx

import React, { useEffect, useRef } from 'react';
import { Paper, Typography, Box } from '@mui/material';
import type { NetworkData } from '../api/newsApi';
import { useThemeProvider } from '../hooks/useTheme';


interface KeywordNetworkProps {
  data?: NetworkData;
}

export const KeywordNetwork: React.FC<KeywordNetworkProps> = ({ data }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const { theme } = useThemeProvider(); // 테마 가져오기

  useEffect(() => {
    if (!containerRef.current || !data || !data.nodes.length || !data.edges.length) {
        if (containerRef.current) containerRef.current.innerHTML = '';
        return;
    }

    const container = containerRef.current;
    const canvas = document.createElement('canvas');
    const width = container.offsetWidth;
    const height = 500;
    canvas.width = width;
    canvas.height = height;
    container.innerHTML = '';
    container.appendChild(canvas);

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const nodes = data.nodes.map((node) => ({
      ...node,
      x: Math.random() * width,
      y: Math.random() * height,
    }));

    const drawNetwork = () => {
      ctx.clearRect(0, 0, width, height);

      // 연결선(Edges) 그리기
      ctx.strokeStyle = theme.palette.divider;
      ctx.lineWidth = 1;
      data.edges.forEach(edge => {
        const sourceNode = nodes.find(n => n.id === edge.source);
        const targetNode = nodes.find(n => n.id === edge.target);
        if (sourceNode && targetNode) {
          ctx.beginPath();
          ctx.moveTo(sourceNode.x, sourceNode.y);
          ctx.lineTo(targetNode.x, targetNode.y);
          ctx.stroke();
        }
      });

      // 노드(Nodes) 그리기
      nodes.forEach((node) => {
        const radius = Math.max(Math.sqrt(node.value) * 2.5, 5);
        ctx.fillStyle = theme.palette.primary.main;
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI);
        ctx.fill();
        ctx.fillStyle = theme.palette.text.primary;
        ctx.font = '12px "Roboto", sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(node.label, node.x, node.y - radius - 5);
      });
    };

    drawNetwork();

  }, [data, theme]);

  if (!data || !data.nodes.length || !data.edges.length) {
    return (
        <Paper sx={{ p: 3, height: 500, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
            <Typography color="text.secondary">
                키워드 연결 데이터가 부족합니다.
            </Typography>
        </Paper>
    );
  }

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        키워드 네트워크
      </Typography>
      <div ref={containerRef} style={{ minHeight: 500, width: '100%' }} />
    </Paper>
  );
};


