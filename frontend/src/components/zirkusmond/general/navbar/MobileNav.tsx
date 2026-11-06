import { Menu, XIcon } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { useTranslation } from "react-i18next";

import { Button } from "#/components/ui/button.tsx";
import { Separator } from "#/components/ui/separator.tsx";
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "#/components/ui/sheet.tsx";
import LocaleSwitcher from "./LocaleSwitcher.tsx";

import type { NavItem } from "./nav-items.ts";
import Logo from "./Logo.tsx";
import SectionDivider from "../SectionDivider.tsx";

interface MobileNavProps {
  items: NavItem[];
}

export default function MobileNav({ items }: MobileNavProps) {
  const { t } = useTranslation();

  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          aria-label="Toggle menu"
          className="md:hidden"
        >
          <Menu className="size-8" />
        </Button>
      </SheetTrigger>
      <SheetContent
        showCloseButton={false}
        className="border-l-2 border-primary bg-[url(/images/general/bg_pattern.webp)] bg-repeat w-full max-w-dvw"
      >
        <SheetHeader className="flex flex-row justify-between">
          <SheetTitle className="text-primary text-4xl max-w-1/2">
            <SheetClose asChild>
              <Link to="/" className="flex max-w-16">
                <Logo asLink={false} />
              </Link>
            </SheetClose>
          </SheetTitle>
          <SheetClose className="max-w-16">
            <XIcon className="text-primary" width={64} height={64} />
          </SheetClose>
        </SheetHeader>
        <div className="flex flex-col h-full justify-between">
          <nav className="flex flex-col items-center gap-12 p-4 grow justify-center">
            {items.map((item) => {
              const Icon = item.icon;
              return item.external ? (
                <SheetClose key={item.href} asChild>
                  <a
                    href={item.href}
                    className="text-xl sm:text-2xl text-primary flex items-center gap-3"
                  >
                    <Icon className="size-6 sm:size-7" />
                    {t(item.labelKey)}
                  </a>
                </SheetClose>
              ) : (
                <SheetClose key={item.href} asChild>
                  <Link
                    to={item.href}
                    className="text-4xl sm:text-xl text-primary flex items-center gap-3"
                  >
                    <Icon className="size-8 sm:size-7" />
                    {t(item.labelKey)}
                  </Link>
                </SheetClose>
              );
            })}
          </nav>
          <div className="my-6">
            <SectionDivider type="flower" />
            <Separator className="bg-primary mb-0.5" />
            <Separator className="bg-primary" />
          </div>
          <div className="flex flex-col gap-12 align-middle justify-center p-4 mx-auto">
            <LocaleSwitcher isMobile />
          </div>
          <SectionDivider type="moon" />
        </div>
      </SheetContent>
    </Sheet>
  );
}
