import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { AgentState } from '../types';

interface AgentOrbProps {
  state: AgentState;
  audioVolume: number;
}

export const AgentOrb: React.FC<AgentOrbProps> = ({ state, audioVolume }) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const volumeRef = useRef(audioVolume);
  const stateRef = useRef(state);

  useEffect(() => {
    volumeRef.current = audioVolume;
  }, [audioVolume]);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    const width = container.clientWidth || 340;
    const height = container.clientHeight || 340;

    // 1. Cena, Câmera e Renderer Three.js
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.z = 20;

    const renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
      powerPreference: 'high-performance',
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    const orbGroup = new THREE.Group();
    scene.add(orbGroup);

    // 2. Anéis Concêntricos Holográficos
    // Anel Externo Segmentado
    const outerRingGeo = new THREE.RingGeometry(5.6, 6.0, 72);
    const outerRingMat = new THREE.MeshBasicMaterial({
      color: 0x00f0ff,
      side: THREE.DoubleSide,
      wireframe: true,
      transparent: true,
      opacity: 0.8,
    });
    const outerRing = new THREE.Mesh(outerRingGeo, outerRingMat);
    orbGroup.add(outerRing);

    // Anel Intermediário com Ticks
    const midRingGeo = new THREE.RingGeometry(4.2, 4.8, 36);
    const midRingMat = new THREE.MeshBasicMaterial({
      color: 0x00b4d8,
      side: THREE.DoubleSide,
      wireframe: true,
      transparent: true,
      opacity: 0.85,
    });
    const midRing = new THREE.Mesh(midRingGeo, midRingMat);
    orbGroup.add(midRing);

    // Anel Interno Fino
    const innerRingGeo = new THREE.RingGeometry(2.8, 3.1, 32);
    const innerRingMat = new THREE.MeshBasicMaterial({
      color: 0x90e0ef,
      side: THREE.DoubleSide,
      wireframe: true,
      transparent: true,
      opacity: 0.75,
    });
    const innerRing = new THREE.Mesh(innerRingGeo, innerRingMat);
    orbGroup.add(innerRing);

    // 3. Núcleo Icosaedro Holográfico Central
    const coreGeo = new THREE.IcosahedronGeometry(2.0, 1);
    const coreMat = new THREE.MeshBasicMaterial({
      color: 0x00f0ff,
      wireframe: true,
      transparent: true,
      opacity: 0.9,
    });
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    orbGroup.add(coreMesh);

    // Esfera Interna Sólida Suave (Glow de Núcleo)
    const glowGeo = new THREE.SphereGeometry(1.2, 24, 24);
    const glowMat = new THREE.MeshBasicMaterial({
      color: 0x00f0ff,
      transparent: true,
      opacity: 0.45,
      blending: THREE.AdditiveBlending,
    });
    const glowMesh = new THREE.Mesh(glowGeo, glowMat);
    orbGroup.add(glowMesh);

    // 4. Enxame de Partículas Orbitais Reativas
    const particleCount = 240;
    const particleGeo = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const originalPositions = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount * 3; i += 3) {
      const theta = Math.random() * Math.PI * 2;
      const radius = 3.0 + Math.random() * 4.5;
      const x = Math.cos(theta) * radius;
      const y = Math.sin(theta) * radius;
      const z = (Math.random() - 0.5) * 3.0;

      positions[i] = x;
      positions[i + 1] = y;
      positions[i + 2] = z;

      originalPositions[i] = x;
      originalPositions[i + 1] = y;
      originalPositions[i + 2] = z;
    }

    particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));

    const particleMat = new THREE.PointsMaterial({
      color: 0x00f0ff,
      size: 0.16,
      transparent: true,
      opacity: 0.85,
      blending: THREE.AdditiveBlending,
    });
    const particles = new THREE.Points(particleGeo, particleMat);
    orbGroup.add(particles);

    // 5. Paleta de Cores e Alvos por Estado
    const targetColor = new THREE.Color(0x00f0ff);
    let targetSpeed = 1.0;
    let targetCoreScale = 1.0;

    let animationId: number;
    const clock = new THREE.Clock();

    const animate = () => {
      animationId = requestAnimationFrame(animate);
      const delta = clock.getDelta();
      const time = clock.getElapsedTime();
      const currentVol = volumeRef.current || 0;
      const currentState = stateRef.current;

      // Configuração por estado
      switch (currentState) {
        case 'thinking':
          // Rotação rápida em espiral e âmbar holográfico
          targetColor.setHex(0xffb703);
          targetSpeed = 3.5;
          targetCoreScale = 1.15 + Math.sin(time * 8) * 0.08;
          break;

        case 'listening':
          // Reativo à amplitude da voz do usuário
          targetColor.setHex(0x00f0ff);
          targetSpeed = 1.2 + (currentVol * 0.03);
          targetCoreScale = 1.0 + (currentVol * 0.02);
          break;

        case 'speaking':
          // Modulação fluida simulando emissão de voz em ciano elétrico
          targetColor.setHex(0x38bdf8);
          targetSpeed = 1.8 + Math.sin(time * 4) * 0.4;
          targetCoreScale = 1.1 + Math.sin(time * 10) * 0.12;
          break;

        case 'awaiting_approval':
          // Alerta crítico vermelho
          targetColor.setHex(0xff3366);
          targetSpeed = 1.5;
          targetCoreScale = 1.05 + Math.sin(time * 6) * 0.06;
          break;

        case 'error':
          targetColor.setHex(0xef4444);
          targetSpeed = 0.5;
          targetCoreScale = 0.9;
          break;

        case 'idle':
        default:
          // Pulso lento harmônico suave
          targetColor.setHex(0x00d2ff);
          targetSpeed = 0.8;
          targetCoreScale = 1.0 + Math.sin(time * 2) * 0.04;
          break;
      }

      // Transição suave contínua de cores (lerp)
      outerRingMat.color.lerp(targetColor, 0.08);
      midRingMat.color.lerp(targetColor, 0.08);
      innerRingMat.color.lerp(targetColor, 0.08);
      coreMat.color.lerp(targetColor, 0.08);
      glowMat.color.lerp(targetColor, 0.08);
      particleMat.color.lerp(targetColor, 0.08);

      // Rotações opostas suaves
      outerRing.rotation.z += delta * 0.45 * targetSpeed;
      midRing.rotation.z -= delta * 0.75 * targetSpeed;
      innerRing.rotation.z += delta * 0.6 * targetSpeed;

      coreMesh.rotation.x += delta * 0.5 * targetSpeed;
      coreMesh.rotation.y += delta * 0.8 * targetSpeed;

      // Escala suave do núcleo
      coreMesh.scale.lerp(
        new THREE.Vector3(targetCoreScale, targetCoreScale, targetCoreScale),
        0.1
      );
      glowMesh.scale.lerp(
        new THREE.Vector3(targetCoreScale * 1.1, targetCoreScale * 1.1, targetCoreScale * 1.1),
        0.1
      );

      // Deformação dinâmica das partículas com base no áudio
      const posAttr = particleGeo.attributes.position as THREE.BufferAttribute;
      const posArray = posAttr.array as Float32Array;
      const expansion = currentState === 'listening' ? (currentVol * 0.04) : (Math.sin(time * 3) * 0.15);

      for (let i = 0; i < particleCount * 3; i += 3) {
        const origX = originalPositions[i];
        const origY = originalPositions[i + 1];
        const origZ = originalPositions[i + 2];

        // Pulsação radial
        const factor = 1.0 + expansion;
        posArray[i] = origX * factor;
        posArray[i + 1] = origY * factor;
        posArray[i + 2] = origZ + Math.sin(time * 2 + i) * 0.2;
      }
      posAttr.needsUpdate = true;
      particles.rotation.z += delta * 0.25 * targetSpeed;

      renderer.render(scene, camera);
    };

    animate();

    const handleResize = () => {
      if (!container) return;
      const newW = container.clientWidth || 340;
      const newH = container.clientHeight || 340;
      camera.aspect = newW / newH;
      camera.updateProjectionMatrix();
      renderer.setSize(newW, newH);
    };

    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener('resize', handleResize);

      // Descarte de memória seguro
      outerRingGeo.dispose();
      outerRingMat.dispose();
      midRingGeo.dispose();
      midRingMat.dispose();
      innerRingGeo.dispose();
      innerRingMat.dispose();
      coreGeo.dispose();
      coreMat.dispose();
      glowGeo.dispose();
      glowMat.dispose();
      particleGeo.dispose();
      particleMat.dispose();
      renderer.dispose();

      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []);

  return (
    <div className="relative flex items-center justify-center select-none">
      <div ref={mountRef} className="w-72 h-72 sm:w-84 sm:h-84 md:w-96 md:h-96" />
      {/* Retículas e anéis concêntricos holográficos decorativos */}
      <div className="absolute inset-0 rounded-full border border-jarvis-border/40 pointer-events-none animate-pulse" />
      <div className="absolute inset-4 rounded-full border border-dashed border-jarvis-cyan/20 pointer-events-none" />
    </div>
  );
};
