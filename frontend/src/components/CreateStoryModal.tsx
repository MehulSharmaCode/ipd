import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';

interface CreateStoryModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess: () => void;
}

export default function CreateStoryModal({ isOpen, onClose, onSuccess }: CreateStoryModalProps) {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const [formData, setFormData] = useState({
        title: '',
        content: '',
        crop_type: '',
        location_state: '',
        location_district: '',
        media_url: '',
    });

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        try {
            // Clean up empty optional fields
            const payload: any = { ...formData };
            if (!payload.media_url) {
                delete payload.media_url;
            }

            await api.post('/stories', payload);

            // Reset form
            setFormData({
                title: '',
                content: '',
                crop_type: '',
                location_state: '',
                location_district: '',
                media_url: '',
            });
            onSuccess();
        } catch (err: any) {
            console.error(err);
            if (err.response?.status === 401) {
                setError("You must be logged in to post a story.");
            } else {
                setError("Failed to submit story. Only verified farmers can post or invalid data provided.");
            }
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <AnimatePresence>
            <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    className="bg-white dark:bg-slate-900 w-full max-w-2xl rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col max-h-[90vh]"
                >
                    {/* Header */}
                    <div className="flex items-center justify-between p-6 border-b border-slate-100 dark:border-slate-800">
                        <h2 className="text-xl font-bold text-slate-900 dark:text-white">Share Your Success Story</h2>
                        <button
                            onClick={onClose}
                            className="text-slate-400 hover:text-slate-600 dark:hover:text-white transition-colors p-1"
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>

                    {/* Body */}
                    <div className="p-6 overflow-y-auto w-full">
                        {error && (
                            <div className="mb-6 p-4 rounded-lg bg-red-50 text-red-600 border border-red-200 text-sm font-medium">
                                {error}
                            </div>
                        )}

                        <form id="story-form" onSubmit={handleSubmit} className="space-y-5">
                            <div>
                                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">Story Title <span className="text-red-500">*</span></label>
                                <input
                                    type="text"
                                    name="title"
                                    required
                                    placeholder="e.g., How I doubled my wheat yield using PM-Kisan funds"
                                    value={formData.title}
                                    onChange={handleChange}
                                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-lg focus:ring-emerald-500 focus:border-emerald-500 block p-3"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">Detailed Story <span className="text-red-500">*</span></label>
                                <textarea
                                    name="content"
                                    required
                                    rows={5}
                                    placeholder="Share your journey, challenges faced, and how the platform or scheme helped you..."
                                    value={formData.content}
                                    onChange={handleChange}
                                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-lg focus:ring-emerald-500 focus:border-emerald-500 block p-3 resize-none"
                                />
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                                <div>
                                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">Crop Type</label>
                                    <input
                                        type="text"
                                        name="crop_type"
                                        placeholder="e.g., Wheat, Cotton"
                                        value={formData.crop_type}
                                        onChange={handleChange}
                                        className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-lg focus:ring-emerald-500 focus:border-emerald-500 block p-3"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">Your State</label>
                                    <input
                                        type="text"
                                        name="location_state"
                                        placeholder="e.g., Maharashtra"
                                        value={formData.location_state}
                                        onChange={handleChange}
                                        className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-lg focus:ring-emerald-500 focus:border-emerald-500 block p-3"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">Media Link (Optional Video/Audio)</label>
                                <input
                                    type="url"
                                    name="media_url"
                                    placeholder="https://youtube.com/..."
                                    value={formData.media_url}
                                    onChange={handleChange}
                                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white text-sm rounded-lg focus:ring-emerald-500 focus:border-emerald-500 block p-3"
                                />
                                <p className="mt-1.5 text-xs text-slate-500">Provide a link to a YouTube video or external audio explaining your success.</p>
                            </div>
                        </form>
                    </div>

                    {/* Footer */}
                    <div className="p-6 border-t border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50 flex justify-end gap-3 mt-auto">
                        <Button variant="outline" onClick={onClose} disabled={loading} className="border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300">
                            Cancel
                        </Button>
                        <Button form="story-form" type="submit" disabled={loading} className="bg-emerald-600 hover:bg-emerald-500 text-white min-w-[120px]">
                            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Publish Story"}
                        </Button>
                    </div>

                </motion.div>
            </div>
        </AnimatePresence>
    );
}
