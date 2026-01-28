/**
 * 시그널 필터 컴포넌트
 * 등급, 점수, 시그널 타입, 정렬 기준 필터링
 */
"use client"

import { useStore } from "@/store"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Slider } from "@/components/ui/slider"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Card } from "@/components/ui/card"
import { X, Filter } from "lucide-react"

export function SignalFilter() {
  const { filters, sortConfig, setFilters, resetFilters, setSortBy, toggleSortOrder, signals } =
    useStore()

  // 등급 옵션
  const gradeOptions = [
    { value: "S", label: "S 등급", color: "bg-yellow-100 text-yellow-800" },
    { value: "A", label: "A 등급", color: "bg-green-100 text-green-800" },
    { value: "B", label: "B 등급", color: "bg-blue-100 text-blue-800" },
    { value: "C", label: "C 등급", color: "bg-gray-100 text-gray-800" },
  ]

  // 시그널 타입 옵션
  const signalTypeOptions = [
    { value: "all", label: "전체" },
    { value: "VCP", label: "VCP" },
    { value: "종가베팅", label: "종가베팅 V2" },
  ]

  // 정렬 기준 옵션
  const sortOptions = [
    { value: "score", label: "점수순" },
    { value: "grade", label: "등급순" },
    { value: "created_at", label: "생성일순" },
  ]

  // 등급 토글
  const toggleGrade = (grade: string) => {
    const newGrades = filters.grades.includes(grade)
      ? filters.grades.filter((g) => g !== grade)
      : [...filters.grades, grade]
    setFilters({ grades: newGrades })
  }

  // 활성 필터 개수 계산
  const activeFilterCount =
    (filters.grades.length > 0 ? 1 : 0) +
    (filters.minScore > 0 || filters.maxScore < 12 ? 1 : 0) +
    (filters.signalType !== "all" ? 1 : 0)

  return (
    <Card className="p-6 space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5" />
          <h3 className="text-lg font-semibold">필터</h3>
          {activeFilterCount > 0 && (
            <Badge variant="secondary">{activeFilterCount}</Badge>
          )}
        </div>
        <Button variant="ghost" size="sm" onClick={resetFilters}>
          <X className="w-4 h-4 mr-1" />
          초기화
        </Button>
      </div>

      {/* 등급 필터 */}
      <div className="space-y-3">
        <h4 className="text-sm font-medium">등급</h4>
        <div className="flex flex-wrap gap-3">
          {gradeOptions.map((option) => (
            <div key={option.value} className="flex items-center space-x-2">
              <Checkbox
                id={`grade-${option.value}`}
                checked={filters.grades.includes(option.value)}
                onCheckedChange={() => toggleGrade(option.value)}
              />
              <label
                htmlFor={`grade-${option.value}`}
                className="text-sm font-medium cursor-pointer flex items-center gap-2"
              >
                <span className={`px-2 py-1 rounded text-xs ${option.color}`}>
                  {option.label}
                </span>
              </label>
            </div>
          ))}
        </div>
      </div>

      {/* 점수 범위 필터 */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-medium">점수 범위</h4>
          <span className="text-sm text-gray-600">
            {filters.minScore}점 - {filters.maxScore}점
          </span>
        </div>
        <Slider
          min={0}
          max={12}
          step={0.5}
          value={[filters.minScore, filters.maxScore]}
          onValueChange={([min, max]) => setFilters({ minScore: min, maxScore: max })}
          className="py-4"
        />
      </div>

      {/* 시그널 타입 필터 */}
      <div className="space-y-3">
        <h4 className="text-sm font-medium">시그널 타입</h4>
        <Select value={filters.signalType} onValueChange={(value) => setFilters({ signalType: value })}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {signalTypeOptions.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* 정렬 */}
      <div className="space-y-3">
        <h4 className="text-sm font-medium">정렬</h4>
        <div className="flex gap-2">
          <Select value={sortConfig.sortBy} onValueChange={setSortBy}>
            <SelectTrigger className="flex-1">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {sortOptions.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button variant="outline" size="icon" onClick={toggleSortOrder}>
            {sortConfig.order === "desc" ? "↓" : "↑"}
          </Button>
        </div>
      </div>

      {/* 결과 요약 */}
      <div className="pt-4 border-t">
        <p className="text-sm text-gray-600">
          총 <span className="font-semibold">{signals.length}</span>개 중 필터링된 결과
        </p>
      </div>
    </Card>
  )
}
