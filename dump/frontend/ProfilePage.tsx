import React, { useEffect, useState } from 'react';
import api from '@/lib/api.ts';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from 'sonner';
import { Loader2, Save, User, MapPin, Tractor } from 'lucide-react';

export default function ProfilePage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    full_name: '',
    phone_number: '',
    age: '',
    gender: '',
    category: '',
    state: '',
    district: '',
    land_size_hectares: '',
    farmer_type: '',
    primary_crops: '',
  });

  // 1. Fetch existing data on load
  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const res = await api.get('/farmers/me');
        const data = res.data;
        setFormData({
          ...data,
          // Convert arrays/numbers to strings for the form inputs
          age: data.age?.toString() || '',
          land_size_hectares: data.land_size_hectares?.toString() || '',
          primary_crops: data.primary_crops?.join(', ') || '',
        });
      } catch (err) {
        toast.error("Failed to load profile data");
      } finally {
        setLoading(false);
      }
    };
    fetchProfile();
  }, []);

  // 2. Handle Update
  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        ...formData,
        age: parseInt(formData.age),
        land_size_hectares: parseFloat(formData.land_size_hectares),
        primary_crops: formData.primary_crops.split(',').map(c => c.trim()).filter(c => c !== ""),
      };
      
      await api.put('/farmers/me', payload);
      toast.success("Profile updated in database!");
    } catch (err) {
      toast.error("Update failed. Check your connection.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="flex h-screen items-center justify-center font-bold text-emerald-600">Loading your records...</div>;

  return (
    <div className="p-4 md:p-8 max-w-4xl mx-auto">
      <form onSubmit={handleSave} className="space-y-6">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-black text-slate-900 tracking-tight">Your Profile</h1>
          <Button type="submit" className="bg-emerald-600 hover:bg-emerald-700 shadow-lg shadow-emerald-100" disabled={saving}>
            {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
            Save Changes
          </Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Section 1: Personal Details */}
          <Card className="border-none shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg"><User className="h-5 w-5 text-emerald-600"/> Personal Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-2">
                <Label htmlFor="name">Full Name</Label>
                <Input id="name" value={formData.full_name} disabled className="bg-slate-50" />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="phone">Phone Number</Label>
                <Input id="phone" value={formData.phone_number} onChange={e => setFormData({...formData, phone_number: e.target.value})} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <Label>Age</Label>
                  <Input type="number" value={formData.age} onChange={e => setFormData({...formData, age: e.target.value})} />
                </div>
                <div className="grid gap-2">
                  <Label>Gender</Label>
                  <Select value={formData.gender} onValueChange={v => setFormData({...formData, gender: v})}>
                    <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Male">Male</SelectItem>
                      <SelectItem value="Female">Female</SelectItem>
                      <SelectItem value="Other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Section 2: Farm Location */}
          <Card className="border-none shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg"><MapPin className="h-5 w-5 text-emerald-600"/> Location & Category</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-2">
                <Label>State</Label>
                <Input value={formData.state} onChange={e => setFormData({...formData, state: e.target.value})} />
              </div>
              <div className="grid gap-2">
                <Label>District</Label>
                <Input value={formData.district} onChange={e => setFormData({...formData, district: e.target.value})} />
              </div>
              <div className="grid gap-2">
                <Label>Category</Label>
                <Select value={formData.category} onValueChange={v => setFormData({...formData, category: v})}>
                  <SelectTrigger><SelectValue placeholder="Select Category" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="General">General</SelectItem>
                    <SelectItem value="OBC">OBC</SelectItem>
                    <SelectItem value="SC">SC</SelectItem>
                    <SelectItem value="ST">ST</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* Section 3: Land & Crops */}
          <Card className="md:col-span-2 border-none shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg"><Tractor className="h-5 w-5 text-emerald-600"/> Agricultural Details</CardTitle>
              <CardDescription>This data is used by our AI to calculate scheme eligibility.</CardDescription>
            </CardHeader>
            <CardContent className="grid md:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div className="grid gap-2">
                  <Label>Land Size (Hectares)</Label>
                  <Input type="number" step="0.01" value={formData.land_size_hectares} onChange={e => setFormData({...formData, land_size_hectares: e.target.value})} />
                </div>
                <div className="grid gap-2">
                  <Label>Farmer Type</Label>
                  <Select value={formData.farmer_type} onValueChange={v => setFormData({...formData, farmer_type: v})}>
                    <SelectTrigger><SelectValue placeholder="Select Type" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Small">Small (Less than 2 Ha)</SelectItem>
                      <SelectItem value="Marginal">Marginal (1 Ha)</SelectItem>
                      <SelectItem value="Large">Large (Above 10 Ha)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="grid gap-2">
                <Label>Primary Crops (separated by commas)</Label>
                <textarea 
                  className="flex min-h-[100px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  placeholder="Wheat, Rice, Cotton..."
                  value={formData.primary_crops}
                  onChange={e => setFormData({...formData, primary_crops: e.target.value})}
                />
              </div>
            </CardContent>
          </Card>
        </div>
      </form>
    </div>
  );
}