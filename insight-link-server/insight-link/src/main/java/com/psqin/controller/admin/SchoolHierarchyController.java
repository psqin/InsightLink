package com.psqin.controller.admin;

import com.psqin.domain.entity.SysDept;
import com.psqin.domain.entity.Universities;
import com.psqin.result.PageResult;
import com.psqin.result.Result;
import com.psqin.service.SysDeptService;
import com.psqin.service.UniversityService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@Api(tags = "管理员-学校院系专业班级管理接口")
@RestController("AdminSchoolHierarchyController")
@RequestMapping("/admin/school-hierarchy")
@Slf4j
public class SchoolHierarchyController {

    @Autowired
    private UniversityService universityService;

    @Autowired
    private SysDeptService sysDeptService;

    @PostMapping("/universities")
    @ApiOperation("新增学校")
    public Result saveUniversity(@RequestBody Universities universities) {
        universityService.save(universities);
        return Result.success();
    }

    @PutMapping("/universities/{id}")
    @ApiOperation("修改学校")
    public Result updateUniversity(@PathVariable Long id, @RequestBody Universities universities) {
        universities.setId(id);
        universityService.update(universities);
        return Result.success();
    }

    @DeleteMapping("/universities/{id}")
    @ApiOperation("删除学校")
    public Result deleteUniversity(@PathVariable Long id) {
        universityService.deleteById(id);
        return Result.success();
    }

    @GetMapping("/universities/page")
    @ApiOperation("分页查询学校（支持名称/编码模糊）")
    public Result<PageResult> pageUniversities(@RequestParam(defaultValue = "1") Integer page,
                                               @RequestParam(defaultValue = "10") Integer pageSize,
                                               @RequestParam(required = false) String name,
                                               @RequestParam(required = false) String code) {
        return Result.success(universityService.pageQuery(name, code, page, pageSize));
    }

    @PostMapping("/depts")
    @ApiOperation("新增院系/专业/班级")
    public Result saveDept(@RequestBody SysDept sysDept) {
        sysDeptService.save(sysDept);
        return Result.success();
    }

    @PutMapping("/depts/{id}")
    @ApiOperation("修改院系/专业/班级")
    public Result updateDept(@PathVariable Long id, @RequestBody SysDept sysDept) {
        sysDept.setId(id);
        sysDeptService.update(sysDept);
        return Result.success();
    }

    @DeleteMapping("/depts/{id}")
    @ApiOperation("删除院系/专业/班级")
    public Result deleteDept(@PathVariable Long id) {
        sysDeptService.deleteById(id);
        return Result.success();
    }

    @GetMapping("/depts/page")
    @ApiOperation("分页查询院系/专业/班级（支持名称模糊）")
    public Result<PageResult> pageDepts(@RequestParam(defaultValue = "1") Integer page,
                                        @RequestParam(defaultValue = "10") Integer pageSize,
                                        @RequestParam(required = false) Long universityId,
                                        @RequestParam(required = false) Integer deptType,
                                        @RequestParam(required = false) Long parentId,
                                        @RequestParam(required = false) String name) {
        return Result.success(sysDeptService.pageQuery(universityId, deptType, parentId, name, page, pageSize));
    }
}
