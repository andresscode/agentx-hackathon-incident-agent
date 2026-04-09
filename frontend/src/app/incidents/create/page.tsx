import { IncidentForm } from '@/components/blocks/incident-form'

export default function CreateIncidentPage() {
  return (
    <main className="flex-1 flex flex-col items-center justify-center px-4 py-12">
      <div className="mb-8 text-center max-w-lg">
        <h1 className="text-3xl font-bold tracking-tight font-mono">
          Nameless Incidents Center
        </h1>
        <p className="mt-3 text-muted-foreground text-balance">
          Something went wrong? Let us know. Describe the issue and our
          AI-powered team will investigate.
        </p>
      </div>
      <IncidentForm />
    </main>
  )
}
