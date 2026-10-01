import { Button } from "#/components/ui/button.tsx";
import TextField from "#/components/zirkusmond/form/TextField";
import ContentSection from "../general/ContentSection";
import PageHeader from "../general/PageHeader";
import SectionCard from "../general/SectionCard";
import { useTranslation } from "react-i18next";
import { useMutation } from "@tanstack/react-query";
import { postJson } from "#/lib/api";
import type React from "react";
import { useState } from "react";
import { HandCoins, Send } from "lucide-react";

const SOCIAL_LINKS = [
  {
    label: "YouTube",
    href: "https://www.youtube.com/channel/UCa4CK1Fl7ZpTA6mz04wH6CA",
    icon: "/images/icons/youtube.svg",
  },
  {
    label: "Facebook",
    href: "https://de-de.facebook.com/zirkusmond",
    icon: "/images/icons/facebook.svg",
  },
  {
    label: "Instagram",
    href: "https://www.instagram.com/zirkus_mond/",
    icon: "/images/icons/instagram.svg",
  },
];

export default function ContactSection() {
  const { t } = useTranslation();
  const [email, setEmail] = useState("");

  const registerEmailToNewsletter = () =>
    useMutation({
      mutationFn: () => postJson("/newsletter/register", { email: email }),
      onSuccess: () => {
        setEmail("");
      },
      onError: (error) => {
        console.error(`Mailchimp API error for ${email}:`, error);
      },
    });

  const mutation = registerEmailToNewsletter();

  const handleSubmit = (e: React.SubmitEvent<HTMLFormElement>) => {
    e.preventDefault();
    mutation.mutate();
  };

  return (
    <ContentSection>
      <PageHeader>{t("page_contact_title")}</PageHeader>
      <SectionCard className="flex flex-col justify-between gap-12 text-center text-primary lg:flex-row mt-">
        <div className="flex flex-col justify-center align-middle lg:w-1/3">
          <div className="flex items-center justify-evenly py-4">
            {SOCIAL_LINKS.map((social) => (
              <a
                key={social.label}
                href={social.href}
                target="_blank"
                rel="noreferrer"
              >
                <img className="w-12" src={social.icon} alt={social.label} />
              </a>
            ))}
          </div>
          <div className="">
            <p className="p-4 sm:p-6">
              {t("page_contact_reservations")}
              <a
                className="my-4 sm:my-6 block underline"
                href="mailto:mail@zirkusmond.de"
              >
                mail@zirkusmond.de
              </a>
            </p>
          </div>
          <Button
            asChild
            variant={"primary"}
            className="self-center max-w-sm w-full"
          >
            <a href="https://www.paypal.com/donate?hosted_button_id=AA2ZBHH6JHX9E">
              <HandCoins /> {t("page_contact_donate")}
            </a>
          </Button>
        </div>

        <div className="flex justify-center">
          <div>
            <h3 className="my-4 sm:my-6">{t("page_contact_find_us")}</h3>
            <img
              className="m-auto w-9/12 max-w-80"
              src="/images/general/map.webp"
              alt="Der Zirkus liegt in der Nähe der Lili-Henoch-Str."
            />
          </div>
        </div>

        <div className="lg:w-1/3 flex flex-col justify-center align-middle">
          <h3 className="my-4 sm:my-6">{t("page_contact_mailing_list")}</h3>
          <p className="lg:pr-6">{t("page_contact_mailing_description")}</p>
          <p className="pt-3 sm:pt-4 lg:pr-6">
            {t("page_contact_telegram")}{" "}
            <a
              className="underline"
              href="https://t.me/+bTzQFVB2cHc5b4Zm"
              target="_blank"
              rel="noreferrer"
            >
              {t("page_contact_channel")}
            </a>{" "}
            {t("page_contact_telegram_join")}
          </p>
          <form
            className="my-6"
            onSubmit={(e) => {
              handleSubmit(e);
            }}
          >
            <TextField
              id="newsletter-email"
              label={`${t("form_email")}:`}
              name="email"
              type="email"
              required
              value={email}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setEmail(e.target.value)
              }
            />
            {mutation.isSuccess && (
              <p className="text-sm mt-2">
                {t("page_contact_newsletter_success")}
              </p>
            )}
            <Button type="submit" className="mt-4">
              <Send />
              {t("common_submit")}
            </Button>
          </form>
        </div>
      </SectionCard>
    </ContentSection>
  );
}
