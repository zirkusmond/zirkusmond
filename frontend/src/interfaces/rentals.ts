export interface RentalObject {
  id: string;
  name: string;
  description: string;
  image: string;
  link: string;
}

export const MOCK_RENTAL_OBJECTS: RentalObject[] = [
  {
    id: "1",
    name: "Zirkuszelt",
    description: "Ein wunderschönes Zirkuszelt für Ihre Veranstaltung.",
    image: "/images/rentals/tent.webp",
    link: "mailto:mail@zirkusmond.de",
  },
  {
    id: "2",
    name: "Bühne",
    description: "Professionelle Bühne für Shows und Events.",
    image: "/images/rentals/stage.webp",
    link: "mailto:mail@zirkusmond.de",
  },
];
