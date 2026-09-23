import ReactMarkdown, {
  type Components,
  type ExtraProps,
} from "react-markdown";

// react-markdown passes its syntax-tree `node`, which would otherwise land on the DOM element.
function domProps<P extends ExtraProps>(props: P): Omit<P, "node"> {
  const rest = { ...props };
  delete rest.node;
  return rest;
}

const components: Components = {
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
    <ol {...domProps(props)} className="mt-md list-decimal pl-lg first:mt-0" />
  ),
  li: (props) => <li {...domProps(props)} className="mt-xs" />,
  a: (props) => (
    // A new tab, so following a link never leaves the lesson.
    <a
      {...domProps(props)}
      target="_blank"
      rel="noreferrer"
      className="text-tertiary-strong underline hover:text-primary"
    />
  ),
  blockquote: (props) => (
    <blockquote
      {...domProps(props)}
      className="mt-md border-l-2 border-rule pl-md text-meta-text first:mt-0"
    />
  ),
  code: ({ className, ...props }) => (
    <code
      {...domProps(props)}
      // Keeps the `language-*` class a fenced block carries.
      className={`rounded-sm bg-paper-dim px-xs font-mono text-[0.9em] ${className ?? ""}`}
    />
  ),
  pre: (props) => (
    <pre
      {...domProps(props)}
      className="mt-md overflow-x-auto rounded-sm bg-paper-dim p-sm first:mt-0 [&>code]:bg-transparent [&>code]:px-0"
    />
  ),
  hr: (props) => <hr {...domProps(props)} className="mt-lg border-rule" />,
};

/** Raw HTML in `children` renders as text, never as markup. */
export function Markdown({ children }: { children: string }) {
  return (
    <div className="type-body-md measure text-accent-strong">
      <ReactMarkdown components={components}>{children}</ReactMarkdown>
    </div>
  );
}
