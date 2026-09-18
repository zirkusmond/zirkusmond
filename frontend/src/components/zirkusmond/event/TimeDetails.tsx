import { CardContent, CardDescription } from "#/components/ui/card.tsx";
import { useTranslation } from "react-i18next";
import SectionCard from "../general/SectionCard";

interface TimeDetailsProps {
  date: string;
  admissionTime: string;
  soldOut: boolean;
}

export default function TimeDetails({
  date,
  admissionTime,
  soldOut,
}: TimeDetailsProps) {
  const { t } = useTranslation();
  return (
    <SectionCard>
      <CardContent className="relative px-6 sm:px-8 py-3 sm:py-4">
        {soldOut && (
          <img
            src="/images/general/sold_out.png"
            alt="Sold out"
            className="absolute inset-0 z-30 w-full h-full object-contain opacity-60"
          />
        )}
        <CardDescription className="mb-2 font-bold text-center text-base sm:text-lg text-primary">
          {date}
        </CardDescription>
        <p className="font-semibold">
          {t("show_admission")} {admissionTime}
        </p>
      </CardContent>
    </SectionCard>
  );
}
