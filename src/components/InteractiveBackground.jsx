import { useEffect, useRef } from 'react';

const PARTICLE_COUNT = 34;

function createParticles(width, height) {
  return Array.from({ length: PARTICLE_COUNT }, (_, index) => ({
    x: (index * 137.31) % width,
    y: (index * 83.17) % height,
    radius: index % 8 === 0 ? 1.7 : 1,
    speed: 0.08 + (index % 5) * 0.018,
    phase: index * 0.73,
    drift: 14 + (index % 4) * 8,
    depth: 0.04 + (index % 6) * 0.012
  }));
}

export default function InteractiveBackground() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext('2d');
    if (!canvas || !context) return undefined;

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const pointer = { x: 0.72, y: 0.28, targetX: 0.72, targetY: 0.28 };
    let particles = [];
    let frame = 0;
    let width = 0;
    let height = 0;
    let scrollY = 0;
    let targetScrollY = 0;

    const resize = () => {
      const ratio = Math.min(window.devicePixelRatio || 1, 1.75);
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width * ratio;
      canvas.height = height * ratio;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      particles = createParticles(width, height);
    };

    const handlePointer = (event) => {
      pointer.targetX = event.clientX / Math.max(width, 1);
      pointer.targetY = event.clientY / Math.max(height, 1);
    };

    const handleScroll = () => {
      targetScrollY = window.scrollY;
    };

    const draw = (time = 0) => {
      pointer.x += (pointer.targetX - pointer.x) * 0.045;
      pointer.y += (pointer.targetY - pointer.y) * 0.045;
      scrollY += (targetScrollY - scrollY) * 0.08;
      const t = reducedMotion ? 0 : time * 0.00035;
      context.clearRect(0, 0, width, height);
      context.fillStyle = '#fbfbfa';
      context.fillRect(0, 0, width, height);

      const glow = context.createRadialGradient(pointer.x * width, pointer.y * height, 0, pointer.x * width, pointer.y * height, Math.max(width, height) * 0.48);
      glow.addColorStop(0, 'rgba(31, 31, 31, 0.07)');
      glow.addColorStop(0.42, 'rgba(31, 31, 31, 0.022)');
      glow.addColorStop(1, 'rgba(31, 31, 31, 0)');
      context.fillStyle = glow;
      context.fillRect(0, 0, width, height);

      particles.forEach((particle) => {
        const driftX = reducedMotion ? 0 : Math.sin(t * particle.speed * 8 + particle.phase) * particle.drift;
        const driftY = reducedMotion ? 0 : Math.cos(t * particle.speed * 7 + particle.phase) * particle.drift;
        const x = particle.x + driftX + (pointer.x - 0.5) * 20;
        const y = ((particle.y + driftY - scrollY * particle.depth) % (height + 40) + height + 40) % (height + 40) - 20;
        const distance = Math.hypot(x - pointer.x * width, y - pointer.y * height);
        const alpha = Math.max(0.04, 0.16 - distance / Math.max(width, height) * 0.14);
        context.beginPath();
        context.arc(x, y, particle.radius, 0, Math.PI * 2);
        context.fillStyle = `rgba(31, 31, 31, ${alpha})`;
        context.fill();
      });

      if (!reducedMotion) frame = requestAnimationFrame(draw);
    };

    resize();
    handleScroll();
    draw();
    window.addEventListener('resize', resize);
    window.addEventListener('pointermove', handlePointer, { passive: true });
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener('resize', resize);
      window.removeEventListener('pointermove', handlePointer);
      window.removeEventListener('scroll', handleScroll);
    };
  }, []);

  return <canvas ref={canvasRef} className="interactive-background" aria-hidden="true" />;
}