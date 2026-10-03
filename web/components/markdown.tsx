import ReactMarkdown, {
  type Components,
  type ExtraProps,
} from "react-markdown";

export type Tone = "light" | "dark";

// react-markdown passes its syntax-tree `node`, which would otherwise land on the DOM element.
function domProps<P extends ExtraProps>(props: P): Omit<P, "node"> {
  const rest = { ...props };
  delete rest.node;
  return rest;
}

const colors = {
  light: {
    text: "text-accent-strong",
    link: "text-tertiary-strong hover:text-primary",
    quote: "border-rule text-meta-text",
    code: "bg-paper-dim",
    rule: "border-rule",
  },
  dark: {
    text: "text-dark-on-surface",
    link: "text-dark-primary hover:text-dark-primary-strong",
    quote: "border-dark-rule text-dark-on-surface-meta",
    code: "bg-dark-surface-overlay",
    rule: "border-dark-rule",
  },
} satisfies Record<Tone, Record<string, string>>;

function componentsFor(tone: Tone): Components {
  const color = colors[tone];
  return {
    h1: (props) => (
      <h1 {...domProps(props)} className="type-headline-md mt-xl first:mt-0" />
    ),
    h2: (props) => (
      <h2 {...domProps(props)} className="type-headline-sm mt-xl first:mt-0" />
    ),
    h3: (props) => (
      <h3 {...domProps(props)} className="type-label-lg mt-lg first:mt-0" />
    ),
    h4: (props) => (
      <h4 {...domProps(props)} className="type-label-md mt-lg first:mt-0" />
    ),
    h5: (props) => (
      <h5 {...domProps(props)} className="type-label-md mt-lg first:mt-0" />
    ),
    h6: (props) => (
      <h6 {...domProps(props)} className="type-label-md mt-lg first:mt-0" />
    ),
    p: (props) => <p {...domProps(props)} className="mt-md first:mt-0" />,
    ul: (props) => (
      <ul {...domProps(props)} className="mt-md list-disc pl-lg first:mt-0" />
    ),
    ol: (props) => (
      <ol
        {...domProps(props)}
        className="mt-md list-decimal pl-lg first:mt-0"
      />
    ),
    li: (props) => <li {...domProps(props)} className="mt-xs" />,
    a: (props) => (
      // A new tab, so following a link never leaves the lesson.
      <a
        {...domProps(props)}
        target="_blank"
        rel="noreferrer"
        className={`underline ${color.link}`}
      />
    ),
    blockquote: (props) => (
      <blockquote
        {...domProps(props)}
        className={`mt-md border-l-2 pl-md first:mt-0 ${color.quote}`}
      />
    ),
    code: ({ className, ...props }) => (
      <code
        {...domProps(props)}
        // Keeps the `language-*` class a fenced block carries.
        className={`rounded-sm px-xs font-mono text-[0.9em] ${color.code} ${className ?? ""}`}
      />
    ),
    pre: (props) => (
      <pre
        {...domProps(props)}
        className={`mt-md overflow-x-auto rounded-sm p-sm first:mt-0 [&>code]:bg-transparent [&>code]:px-0 ${color.code}`}
      />
    ),
    hr: (props) => (
      <hr {...domProps(props)} className={`mt-lg ${color.rule}`} />
    ),
  };
}

const components: Record<Tone, Components> = {
  light: componentsFor("light"),
  dark: componentsFor("dark"),
};

/** Raw HTML in `children` renders as text, never as markup. */
export function Markdown({
  children,
  tone = "light",
}: {
  children: string;
  tone?: Tone;
}) {
  return (
    <div className={`type-body-md measure ${colors[tone].text}`}>
      <ReactMarkdown components={components[tone]}>{children}</ReactMarkdown>
    </div>
  );
}
