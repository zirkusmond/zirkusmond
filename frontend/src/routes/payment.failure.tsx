import { createFileRoute, Link } from "@tanstack/react-router";

import PageContainer from "#/components/zirkusmond/general/PageContainer";
import PageHeader from "#/components/zirkusmond/general/PageHeader";
import ContentSection from "#/components/zirkusmond/general/ContentSection";
import SectionCard from "#/components/zirkusmond/general/SectionCard";
import SectionDivider from "#/components/zirkusmond/general/SectionDivider";
import { Button } from "#/components/ui/button";
import { useTranslation } from "react-i18next";
import { Home } from "lucide-react";

interface PaymentFailureSearch {
  paymentId?: string;
  eventShowId?: number;
}

const validatePaymentFailureSearch = (
  search: Record<string, unknown>,
): PaymentFailureSearch => {
  const result = {
    paymentId:
      typeof search.paymentId === "string" ? search.paymentId : undefined,
    eventShowId:
      typeof search.eventShowId === "number" ? search.eventShowId : undefined,
  };
  return result;
};

const RouteComponent = () => {
  const { t } = useTranslation();
  const { paymentId, eventShowId } = Route.useSearch();

  return (
    <PageContainer>
      <PageHeader>{t("page_payment_failure_title")}</PageHeader>

      <ContentSection className="text-center text-white max-w-2xl mx-auto">
        <SectionCard className="space-y-6">
          <h4 className="font-semibold">{t("page_payment_failure_heading")}</h4>
          {eventShowId && (
            <Button asChild>
              <Link
                to="/reserve/$showId"
                params={{ showId: String(eventShowId) }}
                className="mx-auto"
              >
                {t("page_payment_failure_try_again")}
              </Link>
            </Button>
          )}

          <p>
            {t("page_payment_failure_contact")}{" "}
            <a
              href={`mailto:reservation@zirkusmond.de${paymentId ? `?subject=Payment error for ${paymentId}` : ""}`}
              className="text-primary hover:underline"
            >
              reservation@zirkusmond.de
            </a>
            {paymentId && (
              <>
                {" "}
                {t("page_payment_failure_mention_id")} {paymentId}
              </>
            )}
          </p>
        </SectionCard>
        <SectionDivider type="flower" />
        <Button asChild>
          <Home />
          <Link to="/">{t("button_back_to_home")}</Link>
        </Button>
      </ContentSection>
    </PageContainer>
  );
};

export const Route = createFileRoute("/payment/failure")({
  validateSearch: validatePaymentFailureSearch,
  component: RouteComponent,
});
