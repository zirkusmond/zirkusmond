// import ContentSection from "#/components/zirkusmond/general/ContentSection";
// import PageContainer from "#/components/zirkusmond/general/PageContainer";
// import PageHeader from "#/components/zirkusmond/general/PageHeader";
// import SectionCard from "#/components/zirkusmond/general/SectionCard";
// import SectionDivider from "#/components/zirkusmond/general/SectionDivider";
// import { createFileRoute } from "@tanstack/react-router";
// import { useTranslation } from "react-i18next";

// export const Route = createFileRoute("/s/$showId/stats")({
//   validateSearch: (search: Record<string, unknown>) => ({
//     token: typeof search.token === "string" ? search.token : "",
//   }),
//   loader: async ({ params, search }) => {
//     return await getShowStats({
//       data: { showId: params.showId, token: search.token },
//     });
//   },
//   component: RouteComponent,
// });
//     <PageContainer>
//       <PageHeader>{t("ticket_sales")}</PageHeader>

//       <ContentSection className="text-center text-white max-w-2xl mx-auto">
//         {/* <SectionCard className="space-y-6"> */}
//       </ContentSection>
//     </PageContainer>
//   );
// }
