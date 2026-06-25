"use client";

import { useState } from "react";
import { Loader2, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface ScanFormProps {
  onStart: (domain: string) => void;
  onReset: () => void;
  isBusy: boolean;
  hasScan: boolean;
}

export function ScanForm({ onStart, onReset, isBusy, hasScan }: ScanFormProps) {
  const [domain, setDomain] = useState("");

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    const value = domain.trim();
    if (value && !isBusy) onStart(value);
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-2 sm:flex-row">
      <Input
        type="text"
        inputMode="url"
        autoComplete="off"
        placeholder="example.com"
        aria-label="Target domain"
        value={domain}
        onChange={(e) => setDomain(e.target.value)}
        disabled={isBusy}
        className="font-mono"
      />
      <div className="flex gap-2">
        <Button type="submit" disabled={isBusy || domain.trim().length === 0}>
          {isBusy ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Search className="h-4 w-4" />
          )}
          {isBusy ? "Scanning" : "Start scan"}
        </Button>
        {hasScan && (
          <Button type="button" variant="outline" onClick={onReset} disabled={isBusy}>
            New scan
          </Button>
        )}
      </div>
    </form>
  );
}
