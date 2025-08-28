// frontend/news-app/src/components/KeywordNetwork.tsx

import React, { useEffect, useRef } from 'react';
import { Paper, Typography, Box } from '@mui/material';
import type { NetworkData } from '../api/newsApi';

interface KeywordNetworkProps {
  data?: NetworkData;
}

export const KeywordNetwork: React.FC<KeywordNetworkProps> = ({ data }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // 데이터가 없거나, 노드 또는 엣지가 없으면 캔버스를 그리지 않습니다.
    if (!containerRef.current || !data || !data.nodes.length || !data.edges.length) {
        if (containerRef.current) containerRef.current.innerHTML = ''; // 이전 캔버스 정리
        return;
    }

    // Canvas를 이용한 D3-like 네트워크 시각화 (라이브러리 의존성 없음)
    const container = containerRef.current;
    const canvas = document.createElement('canvas');
    const width = container.offsetWidth;
    const height = 500; // 고정 높이
    canvas.width = width;
    canvas.height = height;
    container.innerHTML = ''; // 이전 캔버스 초기화
    container.appendChild(canvas);

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // 노드 초기 위치 설정
    const nodes = data.nodes.map((node) => ({
      ...node,
      x: Math.random() * width,
      y: Math.random() * height,
    }));

    // 그리기 함수
    const drawNetwork = () => {
      ctx.clearRect(0, 0, width, height);

      // 1. 연결선(Edges) 그리기
      ctx.strokeStyle = '#e0e0e0';
      ctx.lineWidth = 1;
      data.edges.forEach(edge => {
        // [수정] 백엔드 데이터 형식(source, target)에 맞춤
        const sourceNode = nodes.find(n => n.id === edge.source);
        const targetNode = nodes.find(n => n.id === edge.target);
        if (sourceNode && targetNode) {
          ctx.beginPath();
          ctx.moveTo(sourceNode.x, sourceNode.y);
          ctx.lineTo(targetNode.x, targetNode.y);
          ctx.stroke();
        }
      });

      // 2. 노드(Nodes) 그리기
      nodes.forEach((node) => {
        const radius = Math.max(Math.sqrt(node.value) * 2.5, 5); // 최소 반지름 보장
        
        // 원 그리기
        ctx.fillStyle = theme.palette.primary.main; // 테마 색상 사용
        ctx.beginPath();
        ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI);
        ctx.fill();

        // 텍스트 레이블
        ctx.fillStyle = theme.palette.text.primary;
        ctx.font = '12px "Roboto", sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(node.label, node.x, node.y - radius - 5);
      });
    };

    drawNetwork();

  }, [data, theme]); // 데이터나 테마가 변경될 때마다 다시 그립니다.

  // 테마를 가져오기 위해 useTheme 훅 사용
  const { theme } = useThemeProvider();


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

// 테마를 사용하기 위해 useThemeProvider 임포트 필요
import { useThemeProvider } from '../hooks/useTheme';
