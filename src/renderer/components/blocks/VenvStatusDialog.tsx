import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/renderer/components/ui/dialog";
import { Button } from "@/renderer/components/ui/button";
import { Badge } from "@/renderer/components/ui/badge";
import { ScrollArea } from "@/renderer/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/renderer/components/ui/tabs";
import { Alert, AlertDescription } from "@/renderer/components/ui/alert";
import {
  Package,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Clock,
  RefreshCw,
  FileText,
  Loader2,
  Info,
  Bug,
  Download
} from "lucide-react";
import { getVenvStatus, getVenvLogs, regenerateVenv } from "@/renderer/lib/api";
import { format } from "date-fns";
import { toast } from "sonner";
import { cn } from "@/renderer/lib/utils";
import { VenvStatus, VenvLog, CheckStatus, CheckResult } from "@/renderer/types/venv";

interface VenvStatusDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  blockPath: string;
  blockName: string;
}

export const VenvStatusDialog = ({
  open,
  onOpenChange,
  blockPath,
  blockName
}: VenvStatusDialogProps) => {
  const [status, setStatus] = useState<VenvStatus | null>(null);
  const [logs, setLogs] = useState<VenvLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [selectedLog, setSelectedLog] = useState<VenvLog | null>(null);

  useEffect(() => {
    if (open) {
      loadData();
    }
  }, [open, blockPath]);

  const loadData = async () => {
    setIsLoading(true);
    try {
      // Load venv status
      const statusRes = await getVenvStatus(blockPath);
      if (statusRes.isOk()) {
        setStatus(statusRes.value);
      }

      // Load venv logs
      const logsRes = await getVenvLogs(blockPath, 10);
      if (logsRes.isOk()) {
        setLogs(logsRes.value.logs || []);
        if (logsRes.value.logs?.length > 0) {
          setSelectedLog(logsRes.value.logs[0]);
        }
      }
    } catch (error) {
      console.error("Failed to load venv data:", error);
      toast.error("Failed to load virtual environment information");
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegenerate = async () => {
    setIsRegenerating(true);
    try {
      const res = await regenerateVenv(blockPath);
      if (res.isOk() && res.value.success) {
        toast.success("Virtual environment regenerated successfully");
        await loadData(); // Reload data
      } else {
        toast.error("Failed to regenerate virtual environment", {
          description: res.error.message || "Unknown error"
        });
      }
    } catch (error) {
      console.error("Failed to regenerate venv:", error);
      toast.error("Failed to regenerate virtual environment");
    } finally {
      setIsRegenerating(false);
    }
  };

  const getStatusIcon = (status: CheckStatus) => {
    switch (status) {
      case CheckStatus.SUCCESS:
        return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case CheckStatus.ERROR:
        return <XCircle className="w-4 h-4 text-destructive" />;
      case CheckStatus.WARNING:
        return <AlertCircle className="w-4 h-4 text-yellow-500" />;
      case CheckStatus.PENDING:
        return <Clock className="w-4 h-4 text-muted-foreground" />;
      case CheckStatus.RUNNING:
        return <Loader2 className="w-4 h-4 text-primary animate-spin" />;
      case CheckStatus.SKIPPED:
        return <Info className="w-4 h-4 text-muted-foreground" />;
      default:
        return <Info className="w-4 h-4 text-muted-foreground" />;
    }
  };

  const getStatusBadge = (valid: boolean) => {
    if (valid) {
      return <Badge variant="outline" className="gap-1 text-green-600">
        <CheckCircle2 className="w-3 h-3" />
        Healthy
      </Badge>;
    }
    return <Badge variant="destructive" className="gap-1">
      <XCircle className="w-3 h-3" />
      Invalid
    </Badge>;
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Package className="w-5 h-5" />
            Virtual Environment: {blockName}
          </DialogTitle>
          <DialogDescription>
            Manage the Python virtual environment for this block
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-8 h-8 animate-spin" />
          </div>
        ) : (
          <Tabs defaultValue="status" className="flex-1">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="status">Status</TabsTrigger>
              <TabsTrigger value="logs">Regeneration Logs</TabsTrigger>
            </TabsList>

            <TabsContent value="status" className="space-y-4">
              {/* Status Overview */}
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div className="space-y-1">
                  <p className="text-sm font-medium">Environment Status</p>
                  <div className="flex items-center gap-4">
                    {status?.exists ? (
                      <>
                        {getStatusBadge(status.valid)}
                        {status.python_version && (
                          <span className="text-sm text-muted-foreground">
                            Python {status.python_version}
                          </span>
                        )}
                      </>
                    ) : (
                      <Badge variant="outline" className="gap-1">
                        <AlertCircle className="w-3 h-3" />
                        Not Created
                      </Badge>
                    )}
                  </div>
                  {status?.last_regenerated && (
                    <p className="text-xs text-muted-foreground">
                      Last regenerated: {format(new Date(status.last_regenerated), "MMM d, yyyy HH:mm")}
                    </p>
                  )}
                </div>
                <Button
                  onClick={handleRegenerate}
                  disabled={isRegenerating}
                  size="sm"
                >
                  {isRegenerating ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Regenerating...
                    </>
                  ) : (
                    <>
                      <RefreshCw className="w-4 h-4 mr-2" />
                      Regenerate
                    </>
                  )}
                </Button>
              </div>

              {/* Installed Packages */}
              {status?.installed_packages && status.installed_packages.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-sm font-medium">Installed Packages ({status.installed_packages.length})</h4>
                  <ScrollArea className="h-[200px] border rounded-lg p-4">
                    <div className="space-y-1">
                      {status.installed_packages.map((pkg, idx) => (
                        <div key={idx} className="flex justify-between text-sm">
                          <span className="font-mono">{pkg.name}</span>
                          <span className="text-muted-foreground">{pkg.version}</span>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </div>
              )}

              {/* Health Checks */}
              {status?.health_checks && status.health_checks.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-sm font-medium">Health Checks</h4>
                  <div className="space-y-2">
                    {status.health_checks.map((check, idx) => (
                      <div key={idx} className="flex items-start gap-2 p-2 border rounded">
                        {getStatusIcon(check.status)}
                        <div className="flex-1">
                          <p className="text-sm font-medium">{check.name}</p>
                          <p className="text-sm text-muted-foreground">{check.message}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </TabsContent>

            <TabsContent value="logs" className="space-y-4">
              {logs.length === 0 ? (
                <Alert>
                  <Info className="w-4 h-4" />
                  <AlertDescription>
                    No regeneration logs available yet.
                  </AlertDescription>
                </Alert>
              ) : (
                <div className="flex gap-4 h-[400px]">
                  {/* Log List */}
                  <div className="w-1/3 border rounded-lg">
                    <ScrollArea className="h-full">
                      <div className="p-2 space-y-1">
                        {logs.map((log, idx) => (
                          <button
                            key={idx}
                            onClick={() => setSelectedLog(log)}
                            className={cn(
                              "w-full text-left p-3 rounded-lg transition-colors",
                              "hover:bg-muted/50",
                              selectedLog === log && "bg-muted"
                            )}
                          >
                            <div className="flex items-start gap-2">
                              {log.success ? (
                                <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5" />
                              ) : (
                                <XCircle className="w-4 h-4 text-destructive mt-0.5" />
                              )}
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium truncate">
                                  {format(new Date(log.start_time), "MMM d, HH:mm")}
                                </p>
                                <p className="text-xs text-muted-foreground">
                                  {log.duration ? `${log.duration.toFixed(1)}s` : "In progress"}
                                </p>
                              </div>
                            </div>
                          </button>
                        ))}
                      </div>
                    </ScrollArea>
                  </div>

                  {/* Log Details */}
                  <div className="flex-1 border rounded-lg">
                    {selectedLog ? (
                      <ScrollArea className="h-full">
                        <div className="p-4 space-y-4">
                          {/* Log Header */}
                          <div className="space-y-2">
                            <div className="flex items-center gap-2">
                              <FileText className="w-4 h-4" />
                              <h4 className="font-medium">Regeneration Log</h4>
                            </div>
                            <div className="text-sm text-muted-foreground space-y-1">
                              <p>Started: {format(new Date(selectedLog.start_time), "PPpp")}</p>
                              {selectedLog.duration && (
                                <p>Duration: {selectedLog.duration.toFixed(2)} seconds</p>
                              )}
                              {selectedLog.error && (
                                <Alert variant="destructive" className="mt-2">
                                  <Bug className="w-4 h-4" />
                                  <AlertDescription>{selectedLog.error}</AlertDescription>
                                </Alert>
                              )}
                            </div>
                          </div>

                          {/* Checks */}
                          <div className="space-y-2">
                            <h5 className="text-sm font-medium">Checks Performed</h5>
                            <div className="space-y-2">
                              {selectedLog.checks.map((check, idx) => (
                                <div key={idx} className="border rounded-lg p-3 space-y-1">
                                  <div className="flex items-start gap-2">
                                    {getStatusIcon(check.status)}
                                    <div className="flex-1">
                                      <p className="text-sm font-medium">{check.name}</p>
                                      <p className="text-sm text-muted-foreground">{check.message}</p>
                                      {check.recovery_action && (
                                        <div className="mt-1 p-2 bg-muted rounded text-xs">
                                          <strong>Action:</strong> {check.recovery_action}
                                        </div>
                                      )}
                                      {check.duration && (
                                        <p className="text-xs text-muted-foreground mt-1">
                                          Took {check.duration.toFixed(3)}s
                                        </p>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      </ScrollArea>
                    ) : (
                      <div className="flex items-center justify-center h-full text-muted-foreground">
                        Select a log to view details
                      </div>
                    )}
                  </div>
                </div>
              )}
            </TabsContent>
          </Tabs>
        )}
      </DialogContent>
    </Dialog>
  );
};
