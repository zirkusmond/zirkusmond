import { createFileRoute } from "@tanstack/react-router";
import { useSuspenseQuery } from "@tanstack/react-query";

import PageContainer from "#/components/zirkusmond/general/PageContainer";
import PageHeader from "#/components/zirkusmond/general/PageHeader";
import ContentSection from "#/components/zirkusmond/general/ContentSection";
import TeamGrid from "#/components/zirkusmond/general/TeamGrid";
import SectionDivider from "#/components/zirkusmond/general/SectionDivider";
import SectionCard from "#/components/zirkusmond/general/SectionCard";
import OpenSource from "#/components/zirkusmond/home/OpenSource";
import { useTranslation } from "react-i18next";
import { teamMembersQueryOptions } from "#/lib/api";

const About = () => {
  const { t } = useTranslation();
  const { data: teamMembers } = useSuspenseQuery(teamMembersQueryOptions());

  return (
    <PageContainer>
      <PageHeader>{t("page_about_title")}</PageHeader>

      <ContentSection>
        <SectionCard className="p-0!">
          <img
            className="w-full"
            src="/images/gallery/img-9.webp"
            alt="Zirkus Mond Image"
          />
          <div className="p-6 md:px-24 md:pb-12">
            <p>{t("page_about_content_p1")}</p>
            <p>{t("page_about_content_p2")}</p>
            <p className="mt-6 font-bold text-xl text-primary text-center">
              {t("page_about_content_p3")}
            </p>
          </div>
        </SectionCard>
      </ContentSection>

      <SectionDivider type="kite" margin="small" className="mb-10" />
      <PageHeader className="mt-12 sm:mt-16">{t("page_about_team")}</PageHeader>
      <TeamGrid members={teamMembers} />

      <SectionDivider type="flower" />
      <OpenSource />
    </PageContainer>
  );
};

export const Route = createFileRoute("/about")({
  loader: async ({ context: { queryClient } }) => {
    await queryClient.query({
      ...teamMembersQueryOptions(),
      staleTime: "static",
    });
  },
  head: () => ({
    meta: [
      { title: "Zirkus Mond – Über uns" },
      {
        name: "description",
        content:
          "Lerne das Team hinter Zirkus Mond kennen – ein Kollektiv internationaler Artist:innen, Tänzer:innen und Künstler:innen in Berlin.",
      },
      {
        name: "keywords",
        content:
          "Zirkus Mond Artist:innen, Artist:innen Berlin, Zirkus Artist:innen, Performance Ensemble, internationale Artist:innen, lokale Künstler:innen, Zirkuskollektiv, Ensemble, interdisziplinäre Kunst, experimentelle Kunst, unabhängige Szene Berlin, Artist, Artistin, Zirkusartist, Zirkusartistin, Performer, Performer:in, Akrobat, Akrobatin, Luftartist, Kunstszene Berlin",
      },
    ],
  }),
  component: About,
});
