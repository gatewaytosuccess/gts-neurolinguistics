export function SectionHeading({
  id,
  eyebrow,
  title,
}: {
  id: string;
  eyebrow: string;
  title: string;
}) {
  return (
    <div>
      <p className="type-label-caps text-accent">{eyebrow}</p>
      <h2
        id={id}
        className="type-headline-sm measure mt-sm lg:type-headline-md"
      >
        {title}
      </h2>
    </div>
  );
}
