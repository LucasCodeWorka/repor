import type { ReactNode } from "react";

type PageContainerProps = {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
};

export function PageContainer({
  eyebrow,
  title,
  description,
  actions,
  children,
}: PageContainerProps) {
  return (
    <div className="page">
      <header className="pageHeader">
        <div>
          {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
          <h1>{title}</h1>
          {description ? <p>{description}</p> : null}
        </div>
        {actions ? <div className="pageActions">{actions}</div> : null}
      </header>
      {children}
    </div>
  );
}
