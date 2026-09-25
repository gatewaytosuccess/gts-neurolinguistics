const INTROS = {
  publish: "This course can't be published until these are fixed:",
  edit: "Not saved: a published course can't be left with these problems.",
};

/** Why a publish, or an edit to a published course, was refused. */
export function PublishProblems({
  refused,
  problems,
}: {
  refused: keyof typeof INTROS;
  problems: string[];
}) {
  return (
    <div
      role="alert"
      className="type-body-sm measure basis-full rounded-sm bg-error-subtle px-sm py-sm text-error"
    >
      <p>{INTROS[refused]}</p>
      <ul className="mt-xs list-disc pl-lg">
        {problems.map((problem, index) => (
          // Two lessons can share a title, so a problem isn't unique.
          <li key={index}>{problem}</li>
        ))}
      </ul>
    </div>
  );
}
