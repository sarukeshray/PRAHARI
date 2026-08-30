import { createContext, useCallback, useContext, useMemo, useState } from 'react'

import { WORKS } from '@/data/works'
import type { FlagStatus, ReviewAction, ReviewEntry, Work } from '@/data/types'

/**
 * Review state for the prototype, held in memory.
 *
 * A finding never changes state on its own. The only transitions are the three a
 * human can take, and each one is recorded with who took it and why. Reloading
 * the page returns the dataset to its starting state, which is what we want for
 * a repeatable demo.
 */

const NEXT_STATUS: Record<ReviewAction, FlagStatus> = {
  INVESTIGATE: 'UNDER_INVESTIGATION',
  OVERRIDE: 'OVERRIDDEN',
  CLEAR: 'CLEARED',
}

/** An override must be justified in writing before it can be submitted. */
export const MIN_JUSTIFICATION = 20

interface ReviewContextValue {
  works: Work[]
  recordReview: (input: {
    workId: string
    flagId: string
    action: ReviewAction
    reviewerName: string
    reviewerRole: string
    justification: string
  }) => void
}

const ReviewContext = createContext<ReviewContextValue | null>(null)

export function ReviewProvider({ children }: { children: React.ReactNode }) {
  const [works, setWorks] = useState<Work[]>(WORKS)

  const recordReview = useCallback<ReviewContextValue['recordReview']>((input) => {
    const entry: ReviewEntry = {
      reviewId: `REV-${Math.floor(Math.random() * 9000 + 1000)}`,
      reviewerName: input.reviewerName,
      reviewerRole: input.reviewerRole,
      action: input.action,
      justification: input.justification,
      decidedAt: new Date().toISOString().slice(0, 10),
    }

    setWorks((prev) =>
      prev.map((w) =>
        w.workId === input.workId
          ? {
              ...w,
              reviews: [entry, ...w.reviews],
              flags: w.flags.map((f) =>
                f.flagId === input.flagId ? { ...f, status: NEXT_STATUS[input.action] } : f,
              ),
            }
          : w,
      ),
    )
  }, [])

  const value = useMemo(() => ({ works, recordReview }), [works, recordReview])
  return <ReviewContext.Provider value={value}>{children}</ReviewContext.Provider>
}

export function useReviews(): ReviewContextValue {
  const ctx = useContext(ReviewContext)
  if (!ctx) throw new Error('useReviews must be used inside ReviewProvider')
  return ctx
}

export function useWork(workId: string | undefined): Work | undefined {
  const { works } = useReviews()
  return works.find((w) => w.workId === workId)
}
