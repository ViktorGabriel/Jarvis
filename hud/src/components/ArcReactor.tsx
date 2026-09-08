import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { AgentState } from '../types';

interface ArcReactorProps {
  state: AgentState;
  audioVolume: number;
}

export const ArcReactor: React.FC<ArcReactorProps> = ({ state, audioVolume }) => {
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

    const width = container.clientWidth || 320;
    const height = container.clientHeight || 320;

    // Cena, Câmera e Renderer
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.z = 18;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.appendChild(renderer.domElement);

    // Grupo Central do Reator Arc
    const reactorGroup = new THREE.Group();
    scene.add(reactorGroup);

    // Cor primária baseada no estado
    const getColor = () => {
      if (stateRef.current === 'awaiting_approval') return 0xff3366; // Vermelho/Alerta
      if (stateRef.current === 'thinking') return 0xffb703;          // Âmbar
      if (stateRef.current === 'speaking') return 0x00f0ff;          // Ciano intenso
      return 0x00d2ff;                                              // Ciano clássico
    };

    // 1. Anel Externo Segmentado
    const ringGeo1 = new THREE.RingGeometry(5.2, 5.5, 64);
    const ringMat1 = new THREE.MeshBasicMaterial({
      color: 0x00f0ff,
      side: THREE.DoubleSide,
      wireframe: true,
      transparent: true,
      opacity: 0.75,
    });
    const outerRing = new THREE.Mesh(ringGeo1, ringMat1);
    reactorGroup.add(outerRing);

    // 2. Anel Intermediário com engrenagens/traços
    const ringGeo2 = new THREE.RingGeometry(3.8, 4.3, 32);
    const ringMat2 = new THREE.MeshBasicMaterial({
      color: 0x00a8ff,
      side: THREE.DoubleSide,
      wireframe: true,
      transparent: true,
      opacity: 0.85,
    });
    const midRing = new THREE.Mesh(ringGeo2, ringMat2);
    reactorGroup.add(midRing);

    // 3. Núcleo Icosaedro Holográfico
    const coreGeo = new THREE.IcosahedronGeometry(2.0, 1);
    const coreMat = new THREE.MeshBasicMaterial({
      color: 0x00f0ff,
      wireframe: true,
      transparent: true,
      opacity: 0.9,
    });
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    reactorGroup.add(coreMesh);

    // 4. Enxame de Partículas Orbitais
    const particleCount = 200;
    const particleGeo = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);

    for (let i = 0; i < particleCount * 3; i += 3) {
      const theta = Math.random() * Math.PI * 2;
      const radius = 2.5 + Math.random() * 4.0;
      positions[i] = Math.cos(theta) * radius;
      positions[i + 1] = Math.sin(theta) * radius;
      positions[i + 2] = (Math.random() - 0.5) * 2;
    }

    particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const particleMat = new THREE.PointsMaterial({
      color: 0x00f0ff,
      size: 0.14,
      transparent: true,
      opacity: 0.8,
      blending: THREE.AdditiveBlending,
    });
    const particles = new THREE.Points(particleGeo, particleMat);
    reactorGroup.add(particles);

    // Loop de Animação
    let animationId: number;
    let clock = new THREE.Clock();

    const animate = () => {
      animationId = requestAnimationFrame(animate);
      const delta = clock.getDelta();
      const currentVol = volumeRef.current;
      const volFactor = 1.0 + (currentVol / 80.0);

      // Atualiza cores dinamicamente
      const activeColor = new THREE.Color(getColor());
      ringMat1.color.lerp(activeColor, 0.1);
      ringMat2.color.lerp(activeColor, 0.1);
      coreMat.color.lerp(activeColor, 0.1);
      particleMat.color.lerp(activeColor, 0.1);

      // Rotações opostas dos anéis
      const speedMult = stateRef.current === 'thinking' ? 3.0 : 1.0;
      outerRing.rotation.z += delta * 0.4 * speedMult * volFactor;
      midRing.rotation.z -= delta * 0.7 * speedMult * volFactor;
      coreMesh.rotation.x += delta * 0.6 * speedMult;
      coreMesh.rotation.y += delta * 0.8 * speedMult;
      particles.rotation.z += delta * 0.2 * speedMult;

      // Pulsação suave do núcleo proporcional ao volume do áudio
      const scale = 1.0 + Math.sin(clock.getElapsedTime() * 4) * 0.05 * volFactor + (currentVol * 0.008);
      coreMesh.scale.set(scale, scale, scale);

      renderer.render(scene, camera);
    };

    animate();

    const handleResize = () => {
      if (!container) return;
      const newW = container.clientWidth || 320;
      const newH = container.clientHeight || 320;
      camera.aspect = newW / newH;
      camera.updateProjectionMatrix();
      renderer.setSize(newW, newH);
    };

    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener('resize', handleResize);
      renderer.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []);

  return (
    <div className="relative flex items-center justify-center">
      <div ref={mountRef} className="w-72 h-72 sm:w-80 sm:h-80" />
      {/* Círculos decorativos concêntricos ao redor */}
      <div className="absolute inset-0 rounded-full border border-jarvis-border pointer-events-none animate-pulse" />
    </div>
  );
};
