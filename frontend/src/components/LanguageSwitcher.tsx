import { useTranslationText } from "@/hooks/useTranslationText";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Globe } from "lucide-react";
import axios from "axios";

export function LanguageSwitcher() {
    const { i18n, t } = useTranslationText();

    const handleLanguageChange = async (lng: string) => {
        await i18n.changeLanguage(lng);

        // Attempt to update backend if a token exists
        const token = localStorage.getItem("token");
        if (token) {
            try {
                await axios.put(
                    "http://localhost:8999/api/farmers/me",
                    { preferred_language: lng },
                    { headers: { Authorization: `Bearer ${token}` } }
                );
            } catch (error) {
                console.error("Failed to update language on backend", error);
            }
        }
    };

    return (
        <Select value={i18n.language || "en"} onValueChange={handleLanguageChange}>
            <SelectTrigger className="w-fit min-w-[130px]">
                <Globe className="mr-2 h-4 w-4" />
                <SelectValue placeholder={t('common.language')} />
            </SelectTrigger>
            <SelectContent>
                <SelectItem value="en">English</SelectItem>
                <SelectItem value="hi">हिंदी</SelectItem>
                <SelectItem value="mr">मराठी</SelectItem>
                <SelectItem value="gu">ગુજરાતી</SelectItem>
            </SelectContent>
        </Select>
    );
}
