"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  FileText,
  BarChart3,
  User,
  DollarSign,
  Building,
} from "lucide-react"

export function LoanApplicationDashboard() {
  const [auditTrailOpen, setAuditTrailOpen] = useState(false)

  const borrowerData = {
    name: "[REDACTED]",
    employmentType: "Self-employed",
    annualIncome: 85000,
    monthlyDebt: 1200,
  }

  const financialRatios = [
    { name: "DTI", value: "36%", status: "pass", threshold: "≤ 43%" },
    { name: "DSCR", value: "0.95", status: "fail", threshold: "≥ 1.2" },
    { name: "LTV", value: "78%", status: "pass", threshold: "≤ 80%" },
  ]

  const riskFlags = ["DSCR below threshold (Required ≥ 1.2)", "Self-employed income without 2-year proof"]

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Agnetic Loan Application</h1>
          <p className="text-gray-600 mt-1">Application Review Dashboard</p>
        </div>
        <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200">
          Under Review
        </Badge>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Borrower Summary */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Borrower Summary
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Name:</span>
                <span className="font-medium">{borrowerData.name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Employment:</span>
                <span className="font-medium flex items-center gap-1">
                  <Building className="h-4 w-4" />
                  {borrowerData.employmentType}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Annual Income:</span>
                <span className="font-medium flex items-center gap-1">
                  <DollarSign className="h-4 w-4" />${borrowerData.annualIncome.toLocaleString()}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Monthly Debt:</span>
                <span className="font-medium">${borrowerData.monthlyDebt.toLocaleString()}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Financial Ratios */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Financial Ratios
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {financialRatios.map((ratio) => (
              <div key={ratio.name} className="flex items-center justify-between p-3 rounded-lg border">
                <div className="flex items-center gap-3">
                  {ratio.status === "pass" ? (
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  ) : (
                    <XCircle className="h-5 w-5 text-red-500" />
                  )}
                  <div>
                    <div className="font-medium">{ratio.name}</div>
                    <div className="text-xs text-gray-500">Required: {ratio.threshold}</div>
                  </div>
                </div>
                <div className={`font-bold ${ratio.status === "pass" ? "text-green-600" : "text-red-600"}`}>
                  {ratio.value}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Risk Assessment */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-500" />
              Risk Assessment
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert className="border-red-200 bg-red-50">
              <AlertTriangle className="h-4 w-4 text-red-500" />
              <AlertDescription className="text-red-700">
                <div className="font-medium mb-2">Risk Flags Identified:</div>
                <ul className="space-y-1 text-sm">
                  {riskFlags.map((flag, index) => (
                    <li key={index} className="flex items-start gap-2">
                      <span className="text-red-500 mt-1">•</span>
                      <span>{flag}</span>
                    </li>
                  ))}
                </ul>
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      </div>

      {/* Recommendation Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-yellow-500" />
            Loan Decision
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3 p-4 bg-yellow-50 rounded-lg border border-yellow-200">
            <div className="flex-shrink-0">
              <Badge className="bg-yellow-100 text-yellow-800 border-yellow-300">Conditional Approval</Badge>
            </div>
            <div>
              <div className="font-medium text-yellow-800">Conditionally Approve (Pending more documents)</div>
              <div className="text-sm text-yellow-700 mt-1">
                Application shows promise but requires additional documentation
              </div>
            </div>
          </div>

          <Alert className="border-blue-200 bg-blue-50">
            <FileText className="h-4 w-4 text-blue-500" />
            <AlertDescription className="text-blue-700">
              <div className="font-medium mb-1">Suggested Follow-up:</div>
              <div className="text-sm">
                "Please upload business bank statements from the last 6 months to verify self-employment income."
              </div>
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>

      {/* Audit Trail */}
      <Card>
        <Collapsible open={auditTrailOpen} onOpenChange={setAuditTrailOpen}>
          <CollapsibleTrigger asChild>
            <CardHeader className="cursor-pointer hover:bg-gray-50 transition-colors">
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  Audit Trail
                </span>
                {auditTrailOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </CardTitle>
            </CardHeader>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <CardContent className="pt-0">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Button variant="outline" className="bg-white text-gray-700 justify-start h-auto p-4">
                  <div className="text-left">
                    <div className="font-medium">GPT Input</div>
                    <div className="text-xs text-gray-500 mt-1">View original application data</div>
                  </div>
                </Button>
                <Button variant="outline" className="bg-white text-gray-700 justify-start h-auto p-4">
                  <div className="text-left">
                    <div className="font-medium">GPT Output</div>
                    <div className="text-xs text-gray-500 mt-1">View AI analysis results</div>
                  </div>
                </Button>
                <Button variant="outline" className="bg-white text-gray-700 justify-start h-auto p-4">
                  <div className="text-left">
                    <div className="font-medium">Ratio Calc Log</div>
                    <div className="text-xs text-gray-500 mt-1">View calculation details</div>
                  </div>
                </Button>
              </div>

              <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                <div className="text-xs text-gray-600 space-y-1">
                  <div>• Application submitted: {new Date().toLocaleDateString()}</div>
                  <div>• Initial screening: Passed</div>
                  <div>• Financial ratio calculation: Completed</div>
                  <div>• Risk assessment: Flagged for review</div>
                  <div>• Decision: Conditional approval pending documentation</div>
                </div>
              </div>
            </CardContent>
          </CollapsibleContent>
        </Collapsible>
      </Card>
    </div>
  )
}
