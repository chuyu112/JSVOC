export default function ProjectModuleTitle({
  projectName,
  moduleName,
  fallbackProjectName = '项目',
}: {
  projectName?: string | null;
  moduleName: string;
  fallbackProjectName?: string;
}) {
  return (
    <h1 className='project-module-title'>
      <span className='project-module-name'>{projectName || fallbackProjectName}</span>
      <span className='project-module-label'>{moduleName}</span>
    </h1>
  );
}
