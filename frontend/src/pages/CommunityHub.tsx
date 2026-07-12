import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Droplets, MapPin, Award, ThumbsUp, MessageCircle, PlayCircle, Plus } from 'lucide-react';

import DarkVeil from '@/components/DarkVeil';
import { useTheme } from '@/components/theme-provider';
import api from '@/lib/api';
import CreateStoryModal from '@/components/CreateStoryModal';

// Animation variants
const fadeUp = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.5 } }
};

const stagger = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { staggerChildren: 0.1 } }
};

interface Story {
    _id: string;
    title: string;
    content: string;
    farmer_name: string;
    crop_type?: string;
    location_state?: string;
    location_district?: string;
    scheme_id?: string;
    media_url?: string;
    upvotes: number;
    created_at: string;
}

export default function CommunityHub() {
    const { theme } = useTheme();

    const [stories, setStories] = useState<Story[]>([]);
    const [loading, setLoading] = useState(true);
    const [isModalOpen, setIsModalOpen] = useState(false);

    // Filters
    const [selectedCrop, setSelectedCrop] = useState('');
    const [selectedState, setSelectedState] = useState('');

    const fetchStories = async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (selectedCrop) params.append('crop', selectedCrop);
            if (selectedState) params.append('state', selectedState);

            const response = await api.get(`/stories?${params.toString()}`);
            setStories(response.data);
        } catch (error) {
            console.error("Failed to fetch stories:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStories();
    }, [selectedCrop, selectedState]);

    const handleUpvote = async (storyId: string) => {
        try {
            const response = await api.post(`/stories/${storyId}/upvote`);

            // Optimitically update the UI
            setStories(stories.map(s => {
                if (s._id === storyId) {
                    return { ...s, upvotes: response.data.upvotes };
                }
                return s;
            }));
        } catch (error) {
            console.error("Failed to upvote:", error);
            alert("You need to be logged in to upvote stories.");
        }
    };

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-[#060a0f] pt-28 pb-20 px-4 sm:px-6 relative overflow-hidden transition-colors duration-300">

            {/* Background Effects */}
            {theme === "dark" && (
                <div className="absolute inset-0 z-0 opacity-40 mix-blend-screen pointer-events-none">
                    <DarkVeil hueShift={10} speed={0.8} />
                </div>
            )}

            <div className="max-w-7xl mx-auto relative z-10">

                {/* Header Section */}
                <motion.div
                    initial="hidden" animate="visible" variants={stagger}
                    className="text-center mb-12"
                >
                    <motion.div variants={fadeUp}>
                        <Badge className="mb-4 px-3 py-1 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800 text-xs font-semibold rounded-full">
                            Community & Guidance
                        </Badge>
                    </motion.div>
                    <motion.h1 variants={fadeUp} className="text-4xl md:text-5xl font-black text-slate-900 dark:text-white mb-4">
                        Farmer Success Stories
                    </motion.h1>
                    <motion.p variants={fadeUp} className="text-slate-500 dark:text-slate-400 max-w-2xl mx-auto mb-8 text-lg">
                        Learn from the experiences of verified farmers across the country. Discover how they maximized yields and benefited from government schemes.
                    </motion.p>

                    <motion.div variants={fadeUp} className="flex justify-center">
                        <Button
                            onClick={() => setIsModalOpen(true)}
                            className="bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-500/20"
                        >
                            <Plus className="w-4 h-4 mr-2" /> Share Your Story
                        </Button>
                    </motion.div>
                </motion.div>

                {/* Filters Section */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="bg-white dark:bg-slate-900/60 p-4 rounded-2xl border border-slate-200 dark:border-slate-800 flex flex-wrap gap-4 items-center justify-between mb-10 shadow-sm backdrop-blur-sm"
                >
                    <div className="flex flex-wrap gap-4 items-center w-full md:w-auto">
                        <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">Filters:</span>

                        <select
                            value={selectedCrop}
                            onChange={(e) => setSelectedCrop(e.target.value)}
                            className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm rounded-lg focus:ring-emerald-500 focus:border-emerald-500 block p-2.5 dark:text-white"
                        >
                            <option value="">All Crops</option>
                            <option value="Rice">Rice</option>
                            <option value="Wheat">Wheat</option>
                            <option value="Cotton">Cotton</option>
                            <option value="Sugarcane">Sugarcane</option>
                        </select>

                        <select
                            value={selectedState}
                            onChange={(e) => setSelectedState(e.target.value)}
                            className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-sm rounded-lg focus:ring-emerald-500 focus:border-emerald-500 block p-2.5 dark:text-white"
                        >
                            <option value="">All States</option>
                            <option value="Maharashtra">Maharashtra</option>
                            <option value="Punjab">Punjab</option>
                            <option value="Gujarat">Gujarat</option>
                            <option value="Haryana">Haryana</option>
                        </select>

                        {(selectedCrop || selectedState) && (
                            <Button variant="ghost" size="sm" onClick={() => { setSelectedCrop(''); setSelectedState(''); }} className="text-slate-500 hover:text-slate-900 dark:hover:text-white">
                                Clear
                            </Button>
                        )}
                    </div>
                </motion.div>

                {/* Stories Feed */}
                {loading ? (
                    <div className="flex justify-center py-20">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500"></div>
                    </div>
                ) : stories.length === 0 ? (
                    <div className="text-center py-20 bg-white dark:bg-slate-900/40 rounded-3xl border border-slate-200 dark:border-slate-800">
                        <MessageCircle className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-4" />
                        <h3 className="text-xl font-bold text-slate-700 dark:text-slate-300 mb-2">No stories found</h3>
                        <p className="text-slate-500">Try adjusting your filters or be the first to share a success story!</p>
                    </div>
                ) : (
                    <motion.div
                        initial="hidden" animate="visible" variants={stagger}
                        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
                    >
                        {stories.map((story) => (
                            <motion.div key={story._id} variants={fadeUp}>
                                <Card className="h-full flex flex-col hover:shadow-xl transition-all duration-300 border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/60 group">
                                    <CardHeader className="pb-3 border-b border-slate-100 dark:border-slate-800">
                                        <div className="flex justify-between items-start">
                                            <div>
                                                <CardTitle className="text-lg font-bold text-slate-900 dark:text-white mb-1 line-clamp-2">
                                                    {story.title}
                                                </CardTitle>
                                                <div className="flex items-center gap-2 text-xs text-slate-500">
                                                    <span className="font-medium text-emerald-600 dark:text-emerald-400">
                                                        {story.farmer_name}
                                                    </span>
                                                    <span>•</span>
                                                    <span>{new Date(story.created_at).toLocaleDateString()}</span>
                                                </div>
                                            </div>
                                            <Badge variant="outline" className="shrink-0 bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-900/20 dark:text-emerald-400 dark:border-emerald-800">
                                                Verified
                                            </Badge>
                                        </div>
                                    </CardHeader>
                                    <CardContent className="flex-1 pt-4 pb-2">
                                        <p className="text-slate-600 dark:text-slate-300 text-sm leading-relaxed mb-4 line-clamp-4">
                                            {story.content}
                                        </p>

                                        <div className="flex flex-wrap gap-2 mb-4">
                                            {story.crop_type && (
                                                <div className="flex items-center text-xs font-medium text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 px-2 py-1 rounded-md">
                                                    <Droplets className="w-3 h-3 mr-1" /> {story.crop_type}
                                                </div>
                                            )}
                                            {story.location_state && (
                                                <div className="flex items-center text-xs font-medium text-blue-700 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 px-2 py-1 rounded-md">
                                                    <MapPin className="w-3 h-3 mr-1" /> {story.location_state}
                                                </div>
                                            )}
                                            {story.scheme_id && (
                                                <div className="flex items-center text-xs font-medium text-violet-700 dark:text-violet-400 bg-violet-50 dark:bg-violet-900/20 px-2 py-1 rounded-md">
                                                    <Award className="w-3 h-3 mr-1" /> Scheme Applied
                                                </div>
                                            )}
                                        </div>

                                        {story.media_url && (
                                            <div className="mt-auto mb-4 p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg flex items-center gap-3 cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
                                                <div className="w-8 h-8 rounded-full bg-emerald-500 flex items-center justify-center shrink-0">
                                                    <PlayCircle className="w-4 h-4 text-white" />
                                                </div>
                                                <div className="text-sm font-medium text-slate-700 dark:text-slate-300 truncate">
                                                    Play Success Story
                                                </div>
                                            </div>
                                        )}
                                    </CardContent>

                                    {/* Action Bar */}
                                    <div className="px-6 py-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-900/30 rounded-b-xl">
                                        <button
                                            onClick={() => handleUpvote(story._id)}
                                            className="flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors"
                                        >
                                            <ThumbsUp className="w-4 h-4" />
                                            {story.upvotes} Helpful
                                        </button>

                                        <button className="flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">
                                            <MessageCircle className="w-4 h-4" />
                                            Discuss
                                        </button>
                                    </div>
                                </Card>
                            </motion.div>
                        ))}
                    </motion.div>
                )}
            </div>

            <CreateStoryModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                onSuccess={() => {
                    setIsModalOpen(false);
                    fetchStories(); // Refresh feed
                }}
            />
        </div>
    );
}
