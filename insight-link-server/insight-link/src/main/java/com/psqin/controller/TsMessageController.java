package com.psqin.controller;

import com.psqin.domain.dto.TsMessageDTO;
import com.psqin.domain.vo.UserVO;
import com.psqin.result.PageResult;
import com.psqin.result.Result;
import com.psqin.service.TsMessageService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 *
 */
@Api(tags = "师生留言相关接口")
@RestController
@RequestMapping("/message")
@Slf4j
public class TsMessageController {

    @Autowired
    private TsMessageService tsMessageService;

    @PostMapping
    @ApiOperation("发送留言信息")
    public Result save(@RequestBody TsMessageDTO tsMessageDTO) {
        tsMessageService.save(tsMessageDTO);
        return Result.success();
    }

    @GetMapping("/contacts")
    @ApiOperation("沟通交流过的人列表")
    public Result<List<UserVO>> contacts() {
        return Result.success(tsMessageService.listContacts());
    }

    @GetMapping("/history/{userId}")
    @ApiOperation("查看与指定用户的沟通记录（分页）")
    public Result<PageResult> history(@PathVariable("userId") Long userId,
                                      @RequestParam(defaultValue = "1") Integer page,
                                      @RequestParam(defaultValue = "20") Integer pageSize) {
        return Result.success(tsMessageService.pageHistory(userId, page, pageSize));
    }

}
