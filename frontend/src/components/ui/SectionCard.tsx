import type { ReactNode } from "react";
import { Box, Card, CardContent, CardHeader, Typography } from "@mui/material";

interface SectionCardProps {
  title: ReactNode;
  children: ReactNode;
  actions?: ReactNode;
  className?: string;
  bodyClassName?: string;
}

export function SectionCard({ title, children, actions }: SectionCardProps) {
  return (
    <Card variant="outlined">
      <CardHeader
        title={typeof title === "string" ? <Typography variant="h6">{title}</Typography> : title}
        action={actions}
        sx={{ borderBottom: 1, borderColor: "divider", py: 1.5 }}
      />
      <CardContent>
        <Box>{children}</Box>
      </CardContent>
    </Card>
  );
}
