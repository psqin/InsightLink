package com.psqin.controller.student;

import com.psqin.domain.dto.StudentMaterialDTO;
import com.psqin.domain.dto.StudentMaterialPageDTO;
import com.psqin.domain.entity.StudentMaterial;
import com.psqin.domain.vo.StudentMaterialVO;
import com.psqin.result.PageResult;
import com.psqin.result.Result;
import com.psqin.service.StuMaterialService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@Api(tags = "材料相关接口")
@RestController
@RequestMapping("/student/material")
@Slf4j
public class StuMaterialController {

    @Autowired
    private StuMaterialService stuMaterialService;

    //材料上传
    @PostMapping
    @ApiOperation("材料上传")
    public Result save(@RequestBody StudentMaterialDTO studentMaterialDTO) {
        log.info("材料上传：{}", studentMaterialDTO);
        stuMaterialService.save(studentMaterialDTO);
        return Result.success();
    }

    //材料删除
    @DeleteMapping("/{id}")
    @ApiOperation("材料删除")
    public Result delete(@PathVariable Long id) {
        log.info("材料删除：{}", id);
        stuMaterialService.delete(id);
        return Result.success();
    }

    //材料修改
    @PutMapping
    @ApiOperation("材料修改")
    public Result update(@RequestBody StudentMaterialDTO studentMaterialDTO) {
        log.info("材料修改：{}", studentMaterialDTO);
        stuMaterialService.update(studentMaterialDTO);
        return Result.success();
    }


    //材料查看
    @GetMapping("/{id}")
    @ApiOperation("材料查看")
    public Result<StudentMaterialVO> getById(@PathVariable Long id) {
        log.info("材料查看：{}", id);
        StudentMaterialVO material = stuMaterialService.getById(id);
        return Result.success(material);
    }

    //材料列表
    @GetMapping("/page")
    @ApiOperation("材料分页列表")
    public Result<PageResult> page(StudentMaterialPageDTO studentMaterialPageDTO) {
        log.info("材料分页列表：{}", studentMaterialPageDTO);
        PageResult pageResult = stuMaterialService.pageQuery(studentMaterialPageDTO);
        return Result.success(pageResult);
    }
}
