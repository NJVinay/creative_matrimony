"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { apiFetch } from "@/lib/api";

export default function OnboardingPage() {
    const router = useRouter();
    const [formData, setFormData] = useState({
        profile_mode: "self",
        display_name: "",
        gender: "female",
        date_of_birth: "",
        city_village: "",
        state: "",
    });
    const [isLoading, setIsLoading] = useState(false);

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);

        try {
            await apiFetch("/profiles", {
                method: "POST",
                body: formData,
            });
            router.push("/dashboard");
        } catch (err: any) {
            console.error(err);
            alert(err.detail || err.message || "Profile creation failed");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950 p-4">
            <Card className="w-full max-w-2xl" glass>
                <div className="mb-8">
                    <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                            className="h-full bg-primary-600 transition-all duration-500 w-1/2"
                        />
                    </div>
                    <h1 className="text-2xl font-serif font-bold mt-4 text-center">
                        Create Your Profile
                    </h1>
                </div>

                <form onSubmit={handleSubmit} className="space-y-6">
                    <div className="grid md:grid-cols-2 gap-6">
                        <div>
                            <label className="block text-sm font-medium mb-2">Profile Created By</label>
                            <div className="flex gap-4">
                                <label className="flex items-center gap-2 border rounded-lg p-3 w-full cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800">
                                    <input
                                        type="radio"
                                        name="profile_mode"
                                        value="self"
                                        checked={formData.profile_mode === "self"}
                                        onChange={handleChange}
                                    />
                                    <span>Self</span>
                                </label>
                                <label className="flex items-center gap-2 border rounded-lg p-3 w-full cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800">
                                    <input
                                        type="radio"
                                        name="profile_mode"
                                        value="parent"
                                        checked={formData.profile_mode === "parent"}
                                        onChange={handleChange}
                                    />
                                    <span>Parent</span>
                                </label>
                            </div>
                        </div>

                        <Input
                            label="Full Name"
                            name="display_name"
                            value={formData.display_name}
                            onChange={handleChange}
                            required
                            placeholder="e.g. Priya Sharma"
                        />

                        <div>
                            <label className="block text-sm font-medium mb-2">Gender</label>
                            <select
                                name="gender"
                                aria-label="Gender"
                                value={formData.gender}
                                onChange={handleChange}
                                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm dark:bg-gray-950 dark:border-gray-800"
                            >
                                <option value="female">Female (Bride)</option>
                                <option value="male">Male (Groom)</option>
                                <option value="other">Other</option>
                            </select>
                        </div>

                        <Input
                            label="Date of Birth"
                            type="date"
                            name="date_of_birth"
                            value={formData.date_of_birth}
                            onChange={handleChange}
                            required
                        />

                        <Input
                            label="City / Village"
                            name="city_village"
                            value={formData.city_village}
                            onChange={handleChange}
                            required
                        />

                        <Input
                            label="State"
                            name="state"
                            value={formData.state}
                            onChange={handleChange}
                            required
                        />
                    </div>

                    <div className="pt-4 flex justify-end">
                        <Button type="submit" size="lg" isLoading={isLoading}>
                            Save & Continue
                        </Button>
                    </div>
                </form>
            </Card>
        </div>
    );
}
