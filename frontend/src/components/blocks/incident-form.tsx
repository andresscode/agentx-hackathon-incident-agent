'use client'

import { AlertCircle, ImagePlus, Loader2, Send, X } from 'lucide-react'
import { useRef, useState } from 'react'
import { useFormStatus } from 'react-dom'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { INCIDENT_FORM } from '@/lib/constants'
import { useIncidentForm } from '@/lib/hooks'

function FieldError({ errors }: { errors?: string[] }) {
  if (!errors?.length) return null
  return (
    <div className="flex flex-col gap-0.5">
      {errors.map((error) => (
        <p key={error} className="text-[0.8rem] text-destructive">
          {error}
        </p>
      ))}
    </div>
  )
}

function SubmitButton() {
  const { pending } = useFormStatus()

  return (
    <Button type="submit" size="lg" disabled={pending} className="w-full">
      {pending ? (
        <>
          <Loader2 className="animate-spin" />
          Submitting...
        </>
      ) : (
        <>
          <Send />
          Submit Incident Report
        </>
      )}
    </Button>
  )
}

function ImageUploadButton({ hasError }: { hasError: boolean }) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [fileName, setFileName] = useState<string | null>(null)

  function handleChange() {
    const file = inputRef.current?.files?.[0]
    setFileName(file?.name ?? null)
  }

  function handleClear() {
    if (inputRef.current) inputRef.current.value = ''
    setFileName(null)
  }

  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor="image">Screenshot (optional)</Label>
      {fileName ? (
        <div className="flex items-center gap-2">
          <span className="max-w-48 truncate text-sm text-muted-foreground">
            {fileName}
          </span>
          <Button
            type="button"
            variant="ghost"
            size="icon-xs"
            onClick={handleClear}
          >
            <X className="size-3.5" />
          </Button>
        </div>
      ) : (
        <div>
          <Button
            type="button"
            variant="outline"
            size="default"
            onClick={() => inputRef.current?.click()}
            aria-invalid={hasError || undefined}
          >
            <ImagePlus />
            Attach Image
          </Button>
        </div>
      )}
      <input
        ref={inputRef}
        type="file"
        id="image"
        name="image"
        accept={INCIDENT_FORM.image.allowedTypes.join(',')}
        className="hidden"
        onChange={handleChange}
      />
    </div>
  )
}

export function IncidentForm() {
  const [state, formAction] = useIncidentForm()

  return (
    <Card className="w-full max-w-lg shadow-md">
      <CardHeader>
        <CardTitle className="text-lg">Report Details</CardTitle>
        <CardDescription>
          Fill in the details below. All fields are required unless marked
          optional.
        </CardDescription>
      </CardHeader>
      <form action={formAction}>
        <CardContent className="flex flex-col gap-5">
          {state.formError && (
            <Alert className="border-rose-200 bg-rose-50 text-rose-900">
              <AlertCircle />
              <AlertTitle>Submission Failed</AlertTitle>
              <AlertDescription>{state.formError}</AlertDescription>
            </Alert>
          )}

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="name">Full Name</Label>
            <Input
              id="name"
              name="name"
              placeholder="Jane Doe"
              defaultValue={state.values?.name}
              maxLength={INCIDENT_FORM.name.max}
              aria-invalid={!!state.fieldErrors?.name || undefined}
            />
            <FieldError errors={state.fieldErrors?.name} />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="email">Email Address</Label>
            <Input
              id="email"
              name="email"
              type="email"
              placeholder="jane@example.com"
              defaultValue={state.values?.email}
              maxLength={INCIDENT_FORM.email.max}
              aria-invalid={!!state.fieldErrors?.email || undefined}
            />
            <FieldError errors={state.fieldErrors?.email} />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="description">Incident Description</Label>
            <Textarea
              id="description"
              name="description"
              placeholder="Describe what happened, what you expected, and any steps to reproduce the issue..."
              rows={5}
              defaultValue={state.values?.description}
              maxLength={INCIDENT_FORM.description.max}
              aria-invalid={!!state.fieldErrors?.description || undefined}
            />
            <FieldError errors={state.fieldErrors?.description} />
          </div>

          <div className="pb-5">
            <ImageUploadButton hasError={!!state.fieldErrors?.image} />
            <FieldError errors={state.fieldErrors?.image} />
          </div>
        </CardContent>

        <CardFooter>
          <SubmitButton />
        </CardFooter>
      </form>
    </Card>
  )
}
