import { CheckCircle2 } from 'lucide-react'
import Link from 'next/link'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardFooter } from '@/components/ui/card'

export default function IncidentCreatedPage() {
  return (
    <main className="flex-1 flex flex-col items-center justify-center px-4 py-12">
      <Card className="w-full max-w-md text-center shadow-md">
        <CardContent className="flex flex-col items-center gap-4 pt-2">
          <div className="flex size-14 items-center justify-center rounded-full bg-chart-3/10">
            <CheckCircle2 className="size-7 text-chart-3" />
          </div>
          <div className="space-y-1.5">
            <h1 className="text-xl font-bold tracking-tight font-(family-name:--font-geist-mono)">
              Incident Reported Successfully
            </h1>
            <p className="text-sm text-muted-foreground text-balance">
              Your incident has been submitted and will be reviewed by our
              AI-powered team. We&apos;ll follow up via email.
            </p>
          </div>
        </CardContent>
        <CardFooter className="justify-center">
          <Button asChild>
            <Link href="/">Report Another Incident</Link>
          </Button>
        </CardFooter>
      </Card>
    </main>
  )
}
