import { Link } from "@tanstack/react-router";

interface LogoProps {
  asLink?: boolean;
}

export default function Logo({ asLink = true }: LogoProps) {
  const image = (
    <img
      className="h-[56.25px] w-[56.25px] object-cover"
      src="/images/logos/logo.webp"
      alt="Zirkusmond logo"
      width={100}
    />
  );

  if (!asLink) return image;

  return (
    <Link to="/" className="flex justify-center">
      {image}
    </Link>
  );
}
