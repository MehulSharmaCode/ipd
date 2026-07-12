import { useState, Suspense, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { useGLTF, PresentationControls, Environment, PerspectiveCamera, Float, Html } from '@react-three/drei';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronLeft, ChevronRight, Sprout, Award, Wind, Thermometer, Droplets } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import * as THREE from 'three';

// --- DATA ---
const cropsData = [
  {
    id: 'wheat',
    name: 'Wheat',
    scientificName: 'Triticum aestivum',
    modelPath: '/models/wheat.glb',
    color: 'from-amber-400 to-orange-600',
    accent: '#f59e0b',
    description: 'A staple grain that sustains billions. India stands as the world\'s second-largest producer, with the golden fields of Punjab and Haryana driving the nation\'s food security.',
    facts: [
      'Contributes 35% to India\'s total food grain production.',
      'Rich in B-vitamins and dietary fiber.',
      'Primary crop for the historic Green Revolution.'
    ],
    botanicalInfo: [
      { label: 'Classification', value: 'Cereal Grain', icon: <Sprout className="h-3 w-3" /> },
      { label: 'Ideal Temp', value: '12°C - 25°C', icon: <Thermometer className="h-3 w-3" /> },
      { label: 'Water Need', value: 'Moderate', icon: <Droplets className="h-3 w-3" /> }
    ],
     scale: 1,
position: [0.25, 0.1, 0] as [number, number, number],
rotation: [0, 0, 0] as [number, number, number]
  },
  {
    id: 'rice',
    name: 'Rice',
    scientificName: 'Oryza sativa',
    modelPath: '/models/rice_plant.glb',
    color: 'from-emerald-400 to-teal-600',
    accent: '#10b981',
    description: 'The lifecycle of water and sun. From the terraced hills of the Northeast to the delta plains of the South, rice is more than a crop—it\'s the heartbeat of Indian culture.',
    facts: [
      'India is the world\'s leading exporter of Basmati rice.',
      'Cultivated in over 43 million hectares across India.',
      'Requires high water retention and warm climate.'
    ],
    botanicalInfo: [
      { label: 'Classification', value: 'Grass Species', icon: <Sprout className="h-3 w-3" /> },
      { label: 'Ideal Temp', value: '25°C - 35°C', icon: <Thermometer className="h-3 w-3" /> },
      { label: 'Water Need', value: 'High (Flood)', icon: <Droplets className="h-3 w-3" /> }
    ],
     scale: 0.06,
position: [0.2, -0.7, 0] as [number, number, number],
rotation: [0, 0, 0] as [number, number, number]
  },
  {
    id: 'corn',
    name: 'Corn',
    scientificName: 'Zea mays',
    modelPath: '/models/corn_old.glb',
    color: 'from-yellow-400 to-amber-500',
    accent: '#fbbf24',
    description: 'The versatile powerhouse. Beyond food and fodder, corn is a critical industrial raw material, powering the biofuel revolution and global supply chains.',
    facts: [
      'Grown in nearly every Indian state across all seasons.',
      'Key ingredient for starch, oil, and ethanol production.',
      'Known as the "Queen of Cereals" due to high genetic yield.'
    ],
    botanicalInfo: [
      { label: 'Classification', value: 'Cereal Leaf', icon: <Sprout className="h-3 w-3" /> },
      { label: 'Ideal Temp', value: '18°C - 27°C', icon: <Thermometer className="h-3 w-3" /> },
      { label: 'Water Need', value: 'Balanced', icon: <Droplets className="h-3 w-3" /> }
    ],
    scale: 0.9,
position: [0.25, -1, 0] as [number, number, number],
rotation: [0, 0, 0] as [number, number, number]
  }
];

// --- 3D COMPONENTS ---

function Model({ path, scale, position, rotation }: { path: string, scale: number, position: [number, number, number], rotation: [number, number, number] }) {
  const { scene } = useGLTF(path);
  const meshRef = useRef<any>(null);

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.005;
      meshRef.current.position.y = position[1] + Math.sin(state.clock.getElapsedTime()) * 0.1;
    }
  });

  return (
    <primitive 
      ref={meshRef}
      object={scene} 
      scale={scale} 
      position={position}
      rotation={rotation}
    />
  );
}

const CropInfoCard = ({ crop, isVisible }: { crop: typeof cropsData[0], isVisible: boolean }) => {
  return (
    <motion.div
      initial={{ opacity: 0, x: 50 }}
      animate={{ opacity: isVisible ? 1 : 0, x: isVisible ? 0 : 50 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
      className="absolute right-4 md:right-12 top-1/2 -translate-y-1/2 w-full max-w-[320px] md:max-w-md z-20"
    >
      <div className="backdrop-blur-xl bg-white/10 dark:bg-slate-900/40 border border-white/20 dark:border-white/10 rounded-[2rem] p-6 md:p-8 shadow-2xl overflow-hidden relative group">
        {/* Ambient Glow */}
        <div className={`absolute -top-24 -right-24 w-48 h-48 bg-gradient-to-br ${crop.color} opacity-20 blur-3xl rounded-full`} />
        
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-4">
            <Badge variant="outline" className="bg-white/5 border-white/20 text-white/80 px-3 py-1 rounded-full text-[10px] tracking-widest uppercase font-bold">
              {crop.scientificName}
            </Badge>
            <div className={`h-2 w-2 rounded-full animate-pulse bg-gradient-to-r ${crop.color}`} />
          </div>

          <h2 className="text-4xl md:text-5xl font-black text-white mb-4 tracking-tighter">
            {crop.name}
          </h2>

          <p className="text-white/70 text-sm md:text-base leading-relaxed mb-8 font-medium">
            {crop.description}
          </p>

          <div className="space-y-6">
            <h4 className="text-xs font-bold text-white/40 uppercase tracking-[0.2em] flex items-center gap-2">
              <Wind className="h-3 w-3" /> Botanical Profile
            </h4>
            
            <div className="space-y-4">
              {crop.botanicalInfo.map((info, i) => (
                <div key={i} className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/10 group/item hover:bg-white/10 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className={`p-1.5 rounded-lg bg-gradient-to-br ${crop.color} text-white`}>
                      {info.icon}
                    </div>
                    <span className="text-white/60 font-medium text-xs uppercase tracking-wider">{info.label}</span>
                  </div>
                  <span className="text-white font-bold text-sm">
                    {info.value}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-8 pt-6 border-t border-white/10 flex items-center justify-between">
             <span className="text-white/30 text-[10px] font-bold uppercase tracking-[0.2em]">Scientific Data 2026</span>
             <div className="flex gap-1">
               <div className={`h-1 w-4 rounded-full bg-gradient-to-r ${crop.color}`} />
               <div className="h-1 w-1 rounded-full bg-white/20" />
               <div className="h-1 w-1 rounded-full bg-white/20" />
             </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default function CropShowcase() {
  const [currentIndex, setCurrentIndex] = useState(0);
  const touchStartX = useRef<number | null>(null);

  const nextCrop = () => setCurrentIndex((prev) => (prev + 1) % cropsData.length);
  const prevCrop = () => setCurrentIndex((prev) => (prev - 1 + cropsData.length) % cropsData.length);

  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX;
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    if (touchStartX.current === null) return;
    const touchEndX = e.changedTouches[0].clientX;
    const diff = touchStartX.current - touchEndX;

    if (Math.abs(diff) > 50) {
      if (diff > 0) nextCrop();
      else prevCrop();
    }
    touchStartX.current = null;
  };

  const activeCrop = cropsData[currentIndex];

  return (
    <section 
      id="crops" 
      className="relative w-screen h-screen overflow-hidden bg-[#0a0a0a]"
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      {/* Background elements */}
      <div className="absolute inset-0 z-0">
        <div className={`absolute top-1/2 left-1/4 -translate-y-1/2 w-[800px] h-[800px] bg-gradient-to-br ${activeCrop.color} opacity-[0.03] blur-[150px] rounded-full transition-all duration-1000`} />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_30%,rgba(255,255,255,0.02)_0%,transparent_50%)]" />
      </div>

      {/* Navigation Layer */}
      <div className="absolute inset-0 z-30 pointer-events-none flex items-center justify-between px-6 md:px-12">
        <button 
          onClick={prevCrop}
          className="pointer-events-auto h-12 w-12 md:h-14 md:w-14 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-white hover:bg-white/10 hover:border-white/20 transition-all group active:scale-90"
        >
          <ChevronLeft className="h-6 w-6 group-hover:-translate-x-1 transition-transform" />
        </button>
        <button 
          onClick={nextCrop}
          className="pointer-events-auto h-12 w-12 md:h-14 md:w-14 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-white hover:bg-white/10 hover:border-white/20 transition-all group active:scale-90"
        >
          <ChevronRight className="h-6 w-6 group-hover:translate-x-1 transition-transform" />
        </button>
      </div>

      {/* Hero Stats (Top Left) */}
      <div className="absolute top-32 left-8 md:left-12 z-20 pointer-events-none">
        <motion.div
          key={activeCrop.id}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col gap-8"
        >
          <div className="flex flex-col gap-1">
            <span className="text-[10px] font-black text-white/30 uppercase tracking-[0.4em]">Agricultural Insights</span>
            <div className="h-1 w-12 bg-white/20 mt-2 rounded-full overflow-hidden">
              <motion.div 
                initial={{ x: '-100%' }}
                animate={{ x: '0%' }}
                transition={{ duration: 0.8 }}
                className={`h-full w-full bg-gradient-to-r ${activeCrop.color}`} 
              />
            </div>
          </div>

          <div className="space-y-6">
            {activeCrop.facts.map((fact, i) => (
              <motion.div 
                key={i}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.2 + i * 0.1 }}
                className="flex items-start gap-4 max-w-[280px]"
              >
                <div className="mt-1 p-1 rounded-md bg-white/5 border border-white/10 shrink-0">
                  <Award className={`h-3 w-3 text-transparent bg-clip-text bg-gradient-to-r ${activeCrop.color}`} />
                </div>
                <p className="text-white/60 text-xs font-semibold leading-relaxed uppercase tracking-wider">
                  {fact}
                </p>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Progress Indicator */}
      <div className="absolute bottom-12 left-1/2 -translate-x-1/2 z-20 flex gap-4">
        {cropsData.map((_, i) => (
          <button
            key={i}
            onClick={() => setCurrentIndex(i)}
            className={`h-1.5 transition-all duration-500 rounded-full ${i === currentIndex ? 'w-12 bg-white' : 'w-4 bg-white/20 hover:bg-white/40'}`}
          />
        ))}
      </div>

      {/* 3D Canvas */}
      <div className="absolute inset-0 z-10">
        <Canvas 
          shadows={{ type: THREE.PCFShadowMap }} 
          gl={{ 
            antialias: true, 
            alpha: true,
            precision: 'highp'
          }}
        >
          <PerspectiveCamera makeDefault position={[0, 0, 8]} fov={35} />
          <ambientLight intensity={0.5} />
          <spotLight position={[10, 10, 10]} angle={0.15} penumbra={1} intensity={2} castShadow />
          <pointLight position={[-10, -10, -10]} intensity={1} />
          
          <Suspense fallback={<Html center><div className="text-white font-black text-2xl tracking-tighter animate-pulse uppercase">Scaling...</div></Html>}>
            <Float
              speed={2} 
              rotationIntensity={0.5} 
              floatIntensity={0.5}
            >
            <PresentationControls
                global
                snap
                rotation={[0, 0.3, 0]}
                polar={[-Math.PI / 3, Math.PI / 3]}
                azimuth={[-Math.PI / 1.4, Math.PI / 1.4]}
              >
                <group scale={1.8} position={[-1.2, 0, 0]}>
                  <Model 
                    key={activeCrop.id}
                    path={activeCrop.modelPath} 
                    scale={activeCrop.scale} 
                    position={activeCrop.position} 
                    rotation={activeCrop.rotation} 
                  />
                </group>
              </PresentationControls>
            </Float>
            <Environment preset="forest" />
          </Suspense>
        </Canvas>
      </div>

      {/* Info Card Overlay */}
      <AnimatePresence mode="wait">
        <CropInfoCard key={activeCrop.id} crop={activeCrop} isVisible={true} />
      </AnimatePresence>
    </section>
  );
}
