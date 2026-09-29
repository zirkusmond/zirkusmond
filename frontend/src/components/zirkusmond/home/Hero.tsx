import SectionDivider from "#/components/zirkusmond/general/SectionDivider";
import type { HeroImage } from "#/interfaces/show";

interface HeroProps {
  heroImage?: HeroImage | null;
}

export default function Hero({ heroImage }: HeroProps) {
  const backgroundImage = heroImage
    ? `url(${heroImage.image})`
    : "url(/images/general/zm_banner.webp)";

  return (
    <div>
      <div
        className="h-[80vh] w-full bg-cover bg-center max-md:h-[50vh] max-[500px]:h-[40vh]"
        style={{ backgroundImage }}
      />
      <SectionDivider type="flower" />
    </div>
  );
}
