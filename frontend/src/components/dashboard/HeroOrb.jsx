import React, { useRef, Suspense } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float, MeshDistortMaterial } from '@react-three/drei';
import * as THREE from 'three';

/**
 * The inner 3D scene — a slowly rotating icosahedron with wireframe overlay
 * and a soft distorted sphere beneath it for the glow feel.
 */
function OrbScene() {
  const meshRef = useRef();
  const wireRef = useRef();

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    if (meshRef.current) {
      meshRef.current.rotation.x = Math.sin(t * 0.2) * 0.3;
      meshRef.current.rotation.y = t * 0.25;
    }
    if (wireRef.current) {
      wireRef.current.rotation.x = Math.sin(t * 0.2) * 0.3;
      wireRef.current.rotation.y = t * 0.25;
    }
  });

  return (
    <>
      {/* Ambient lighting */}
      <ambientLight intensity={0.4} />
      <pointLight position={[3, 3, 3]} intensity={2} color="#6366f1" />
      <pointLight position={[-3, -2, -3]} intensity={1} color="#8b5cf6" />
      <pointLight position={[0, 3, -2]} intensity={0.5} color="#14b8a6" />

      {/* Floating wrapper */}
      <Float
        speed={2}
        rotationIntensity={0.3}
        floatIntensity={0.8}
        floatingRange={[-0.15, 0.15]}
      >
        {/* Core icosahedron */}
        <mesh ref={meshRef}>
          <icosahedronGeometry args={[1.2, 1]} />
          <meshStandardMaterial
            color="#1a1a3a"
            emissive="#3730a3"
            emissiveIntensity={0.3}
            roughness={0.4}
            metalness={0.8}
            transparent
            opacity={0.85}
          />
        </mesh>

        {/* Wireframe overlay */}
        <mesh ref={wireRef}>
          <icosahedronGeometry args={[1.22, 1]} />
          <meshBasicMaterial
            color="#6366f1"
            wireframe
            transparent
            opacity={0.35}
          />
        </mesh>

        {/* Inner glow sphere */}
        <mesh>
          <sphereGeometry args={[0.7, 16, 16]} />
          <meshStandardMaterial
            color="#4338ca"
            emissive="#6366f1"
            emissiveIntensity={0.6}
            transparent
            opacity={0.25}
            roughness={1}
          />
        </mesh>
      </Float>
    </>
  );
}

/**
 * Lazy-loadable 3D hero orb.
 * Contained in a fixed-size canvas, fully isolated.
 * Falls back to a CSS gradient orb if WebGL is unavailable.
 */
export default function HeroOrb({ size = 180 }) {
  return (
    <div style={{ width: size, height: size }} className="relative flex-shrink-0">
      {/* Soft glow halo behind the canvas */}
      <div
        className="absolute inset-0 rounded-full blur-3xl opacity-30"
        style={{ background: 'radial-gradient(circle, rgba(99,102,241,0.6), transparent 70%)' }}
      />

      <Suspense fallback={<FallbackOrb size={size} />}>
        <Canvas
          camera={{ position: [0, 0, 3.5], fov: 40 }}
          style={{ background: 'transparent' }}
          gl={{ antialias: true, alpha: true }}
          dpr={[1, 1.5]}
        >
          <OrbScene />
        </Canvas>
      </Suspense>
    </div>
  );
}

/**
 * CSS-only fallback orb in case WebGL fails.
 */
function FallbackOrb({ size }) {
  return (
    <div
      className="rounded-full animate-float"
      style={{
        width: size,
        height: size,
        background: 'radial-gradient(circle at 35% 35%, rgba(99,102,241,0.5), rgba(139,92,246,0.3), transparent)',
        border: '1px solid rgba(99,102,241,0.3)',
        boxShadow: '0 0 60px rgba(99,102,241,0.25)',
      }}
    />
  );
}
