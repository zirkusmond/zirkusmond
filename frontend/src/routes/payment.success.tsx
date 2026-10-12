import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";

import PageContainer from "#/components/zirkusmond/general/PageContainer";
import PageHeader from "#/components/zirkusmond/general/PageHeader";
import ContentSection from "#/components/zirkusmond/general/ContentSection";
import { reservationDetailQueryOptions } from "#/lib/api";
import { Button } from "#/components/ui/button";
import SectionCard from "#/components/zirkusmond/general/SectionCard";
import SectionCardSkeleton from "#/components/zirkusmond/general/SectionCardSkeleton";
import SectionDivider from "#/components/zirkusmond/general/SectionDivider";
import { useTranslation } from "react-i18next";
import { clearDraft } from "#/components/zirkusmond/reserve/reservationDraft";
import { Home } from "lucide-react";

interface PaymentSuccessSearch {
  reservationId: string;
}

const validatePaymentSuccessSearch = (
  search: Record<string, unknown>,
): PaymentSuccessSearch => {
  return {
    reservationId:
      typeof search.reservationId === "string" ? search.reservationId : "",
  };
};

const RouteComponent = () => {
  const { t } = useTranslation();
  const { reservationId } = Route.useSearch();

  const reservationQuery = useQuery(
    reservationDetailQueryOptions(reservationId),
  );

  useEffect(() => {
    clearDraft();
  }, []);

  return (
    <PageContainer>
      <PageHeader>{t("page_payment_success_title")}</PageHeader>

      <ContentSection
        className="text-center text-white md:text-xl max-w-3xl mx-auto"
        isLoading={reservationQuery.isPending}
        skeleton={<SectionCardSkeleton lines={4} />}
      >
        {reservationQuery.isError ? (
          <SectionCard>
            <p>{t("page_payment_success_error")}</p>
          </SectionCard>
        ) : reservationQuery.data ? (
          <SectionCard className="space-y-6">
            <p>
              {t("page_payment_success_confirmation", {
                email: reservationQuery.data.email,
              })}
            </p>

            {(reservationQuery.data.showTime ||
              reservationQuery.data.admissionTime) && (
              <p>
                {t("page_payment_success_timing", {
                  admissionTime: reservationQuery.data.admissionTime,
                  showTime: reservationQuery.data.showTime,
                })}
              </p>
            )}

            <p>
              {t("page_payment_success_address")} {t("venue_address")}
            </p>

            <p className="text-2xl">{t("page_payment_success_see_you")}</p>
          </SectionCard>
        ) : null}
        <SectionDivider type="flower" />
        <Button asChild>
          <Link to="/">
            <Home />
            {t("button_back_to_home")}
          </Link>
        </Button>
      </ContentSection>
    </PageContainer>
  );
};

export const Route = createFileRoute("/payment/success")({
  validateSearch: validatePaymentSuccessSearch,
  component: RouteComponent,
});
