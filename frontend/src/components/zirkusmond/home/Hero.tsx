import SectionDivider from "#/components/zirkusmond/general/SectionDivider";
import type { HeroImage } from "#/interfaces/show";

interface HeroProps {
  heroImage?: HeroImage | null;
}

export default function Hero({ heroImage }: HeroProps) {
  const desktopImage = heroImage
    ? `url(${heroImage.image})`
    : "url(/images/general/zm_banner.webp)";

  const mobileImage = heroImage?.mobileImage
    ? `url(${heroImage.mobileImage})`
    : desktopImage;

  return (
    <div>
      <div
        className="h-[80vh] w-full bg-cover bg-center max-md:hidden"
        style={{ backgroundImage: desktopImage }}
      />
      <div
        className="hidden h-[50vh] w-full bg-cover bg-center max-md:block max-[500px]:h-[40vh]"
        style={{ backgroundImage: mobileImage }}
      />
      <SectionDivider type="flower" />
    </div>
  );
}
