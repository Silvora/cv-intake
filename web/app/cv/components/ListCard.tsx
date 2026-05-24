"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export function SectionCard({
  title,
  description,
  children,
}: {
  title: string
  description?: string
  children: React.ReactNode
}) {
  return (
    <Card className="border-border/60 bg-card/90 shadow-sm w-full">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        {description ? (
          <CardDescription className="text-xs">{description}</CardDescription>
        ) : null}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  )
}

export function ListCard({
  title,
  items,
}: {
  title: string
  items: string[]
}) {
  return (
    <SectionCard title={title}>
      {items.length ? (
        <ul className="space-y-2 text-sm">
          {items.map((item, index) => (
            <li
              key={`${title}-${index}`}
              className="rounded-md border bg-muted/20 px-3 py-2 leading-6 text-foreground"
            >
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <div className="text-sm text-muted-foreground">暂无</div>
      )}
    </SectionCard>
  )
}
